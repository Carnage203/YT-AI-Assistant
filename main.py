# Monkey patch early to avoid POLLER crash
try:
    import grpc._cython.cygrpc as cygrpc

    def no_op_shutdown(*args, **kwargs):
        pass

    cygrpc.shutdown_grpc_aio = no_op_shutdown
except ImportError:
    pass

from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessage
from langchain_tavily import TavilySearch
import google.generativeai as genai
from langchain_community.document_loaders import YoutubeLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import asyncio, os, json, re


from dotenv import load_dotenv
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

#--------------Main Program-------------------#
class State(TypedDict):
    messages: Annotated[list,add_messages]
    raw_transcript: str
    clean_transcript: str
    segment_size: int
    keypoints: str
    summary_1: str
    summary_2: str
    summary_length: str

llm = init_chat_model("groq:llama3-70b-8192")
genai.configure(api_key=GEMINI_API_KEY)
llm2 = genai.GenerativeModel("gemini-2.5-flash")

def hyperparameter_tuning_tool(transcript_len: int) -> dict:
    """
    Find the best suited chunk_size and segment_size for the text splitter and keypoint extraction.

    Args:
        transcript_len (int): Length of the youtube transcript.

    Returns:
        dict: {'chunk_size': int, 'segment_size': int}
    """
    
    prompt = (
        f"You are an expert technician whose job is to find the best suited chunk_size and segment_size for the RecursiveCharacterTextSplitter and batches which are made by concatinating the chunks from TextSplitter. "
        f"You will be given the length of the youtube transcript and you have to find the best suited chunk_size for it. "
        f"After that based on the chunk_size you will find the best suited segment_size where segment_size is the concatination of those chunks for the asyncronous llm call. "
        f"Keeping in mind LLM used is GEMINI-2.5-FLASH with RPM=5 , TPM=200000 , RPD=150 and input token limit 1,000,000 Output token limit 64,000. "
        f"Thus calculate the best suited chunk_size and segment_size. Keeping in mind for 134190 length of transcript, chunk_size=1000 and segment_size=30. "
        f"Strictly return only the values without any special character or highlight of chunk_size and segment_size in the format:\n"
        f"chunk_size: <value>\nsegment_size: <value>\n"
        f"Here is the length of the youtube transcript: {transcript_len}"
    )
    response = llm.invoke(prompt)
    response = llm.invoke(prompt)
    content = response.content  # Correct attribute!
    chunk_size = int(content.split("chunk_size:")[1].split("\n")[0].strip().replace(',', ''))
    segment_size = int(content.split("segment_size:")[1].split("\n")[0].strip().replace(',', ''))
    return {"chunk_size": chunk_size, "segment_size": segment_size}

def transcript_loader(State):
    """
    Load a YouTube transcript and split it into chunks.
    """
    url = State.get("messages")
    if isinstance(url, list):
        url = url[-1].content 
    if not url:
        raise ValueError("No 'url' found in state for transcript_loader.")
    print(f"Loading transcript from URL: {url}")
    loader = YoutubeLoader.from_youtube_url(
    url,
    add_video_info=False,
    language=["en", "id"])

    text_transcripts = loader.load()
    #print(text_transcripts)
    
    return {"raw_transcript":text_transcripts}
    
def preprocess_transcript(State):
    raw_transcript = State["raw_transcript"]
    raw_transcript = "".join([t.page_content for t in raw_transcript])
    result = hyperparameter_tuning_tool(len(raw_transcript))
    chunk_size = result["chunk_size"]
    segment_size = result["segment_size"]  
    #print(f"Chunk Size: {chunk_size}, Segment Size: {segment_size}")
    text_splitter= RecursiveCharacterTextSplitter(chunk_size=chunk_size)
    chunks = text_splitter.split_text(raw_transcript)
    #print(f"Number of chunks: {len(chunks)}")
    #print(type(chunks),f"First chunk: {chunks[0:3]}")
    return {"clean_transcript":chunks ,"segment_size": segment_size}

def clean_keypoints(keypoints_str: str) :
    """Concise the keypoints further to provide a clean overview."""
    
    final_keypoints = llm2.generate_content(contents=f"""
                    You are provided keypoints/topics extracted from a YouTube video transcript.
                    Your task is to de-duplicate and consolidate these keypoints into a concise list.
                    Make sure to remove any duplicates and keep the keypoints concise.
                    Strictly make sure all topics/keypoints are covered and provide the final list (max 12 topics & 3 subtopics).
                    Here are the keypoints:
                    {keypoints_str}""")
    return final_keypoints.text if final_keypoints else None   
    
async def keypoints(State):
    """ Extracts key points from the transcript chunks asynchronously."""
    chunks = State.get("clean_transcript")
    segment_size = State.get("segment_size", 30) 
    if not chunks:
        print("Error: 'clean_transcript' not found in state or is empty.")
        return {"error_message": "No clean transcript available for keypoint extraction."}

    #print(f"Starting keypoint extraction for {len(chunks)} chunks...")

    all_keypoint_tasks = []
    #print(f"Calculated segment size: {segment_size} chunks per LLM call.")

    all_keypoint_tasks = []

    for i in range(0, len(chunks), segment_size):
        current_segment_chunks = chunks[i : i + segment_size]
        combined_segment_text = " ".join(current_segment_chunks)

        if not combined_segment_text.strip():
            continue

        #print(f"Preparing task for segment {i // segment_size + 1}/{math.ceil(len(chunks)/segment_size)} (length: {len(combined_segment_text)} chars)...")

        prompt = f"""From the following text, extract concise, distinct topics/key-points relevant to technology, study, or important concepts.
        Provide them as a numbered list. Focus on core factual information and avoid repetition within this segment's points.
        MUST return only the list of topics name (maximum 5) and 2 subtopics, without any additional commentary or explanations. The topics should follow a clear logical order (sort of roadmap) and be **highly concise**.
        CRUCIALLY do not repeat any points already extracted from previous segments. DO NOT include any introductory or concluding sentences outside the list.
        TEXT:\n{combined_segment_text}"""

        
        task = llm2.generate_content_async(prompt)
        all_keypoint_tasks.append(task)

    raw_responses = []
    try:
        #print(f"Awaiting {len(all_keypoint_tasks)} concurrent LLM calls...")
        raw_responses = await asyncio.gather(*all_keypoint_tasks)
        #print("All segment keypoint tasks completed.")
    except Exception as e:
        print(f"Error during concurrent keypoint extraction: {e}")
        return {"error_message": f"Failed to extract key points: {e}"}

    segment_keypoints_list = []
    for j, response in enumerate(raw_responses):
        
        segment_keypoints_list.append(response.text.strip())

    final_keypoints_str = "\n".join(segment_keypoints_list)
    keypoints = clean_keypoints(final_keypoints_str)
    if keypoints is None:
        return {"error_message": "Failed to clean keypoints. Please check the input data."}

    return {"keypoints": keypoints}
def summary1(State):
    """
    Provide information on the topics based on keypoints based on LLM knowledgebase.
    """
    topics = State.get("keypoints")
    
    summary_str= llm.invoke(f"""
                You are an expert librarian who knows everything.
                Your task is to explain those topics regareding. Which will help in understanding the topic better.
                Strictly do not include any introductory or concluding sentences outside the list.
                Strictly to cover all the keypoints/topics and do not add information outside of the topics/keypoints.
                Here are the topics/keypoints: {topics}.""")
    return {"summary_1": summary_str.content if summary_str else None}

def summary2(State):
    """
    Provide information on the topics based on keypoints using TavilySearch, following best practices.
    """
    keypoints = State.get("keypoints")

    # Extract main keypoint lines (numbered list)
    if isinstance(keypoints, str):
        # Only keep main topics (lines starting with a digit and a dot)
        topic_lines = [line.strip().split('.', 1)[1].strip()
                       for line in keypoints.split('\n')
                       if line.strip() and line.strip()[0].isdigit() and '.' in line]
    elif isinstance(keypoints, list):
        topic_lines = keypoints
    else:
        topic_lines = []

    search_tool = TavilySearch(max_results=3)
    results = []

    for topic in topic_lines:
        response = search_tool.invoke({"query": topic})
        if isinstance(response, dict) and "results" in response:
            raw_results = response["results"]
        elif response and hasattr(response, "results"):
            raw_results = response.results
        elif isinstance(response, list):
            raw_results = response
        elif hasattr(response, "content"):
            try:
                raw_results = json.loads(response.content)
            except Exception:
                raw_results = []
        else:
            raw_results = []

        for item in raw_results:
            info = item.get("snippet") or item.get("content") or ""
            url = item.get("url") or ""
            if info and url:
                results.append({
                    "keypoint": topic,
                    "information": info,
                    "url": url
                })

    return {"summary_2": results if results else None}

def writer(State):
    """
    Based on the provided information, judge and find the best suited summary for the youtube video.
    """
    user_length = State.get("summary_length", "medium")
    
    summary1 = State.get("summary_1")
    summary2 = State.get("summary_2")
    topics = State.get("keypoints") 
    print("🎯 writer node triggered")
    print("📝 summary_1:", State.get("summary_1"))
    print("📝 summary_2:", State.get("summary_2"))
    print("📝 keypoints:", State.get("keypoints"))
    print("📏 length:", State.get("summary_length"))
    # print(f"Summary 1: {summary1}")
    # print(f"Summary 2: {summary2}")
    
    if isinstance(summary2, list):
        summary2_str = ""
        for idx, item in enumerate(summary2, 1):
            info = item.get("information", "")
            url = item.get("url", "")
            summary2_str += f"- Keypoint{idx}\n- Information/Summary{idx}: {info}\n- URL Information/Summary{idx}: {url}\n"
    else:
        summary2_str = str(summary2) if summary2 else ""
    if summary1 and summary2:
        prompt = f"""
        You are provided with two summaries of a YouTube video. Your task is to stitch the summaries and keypoints/topics together and explain those topics/keypoints with the help of the summaries.
        Make sure to keep the length of the summary {user_length}. Cover all the keypoints/topics in the summary.
        Importantly, do not repeat any information from the summaries or keypoints/topics and STRICTLY cover all the topics and subtopics.
        If you do not have enough information to cover all the topics & subtopics, then you may include any information from your side.
        Follow the following format while prioratizing readibility:
        - Keypoint/Topic (use numbering for each keypoint)
        - Information/Summary (MAKE SURE to break it into multiple lines for better readability)
        - URL (strictly provide only the URL of the source of information)
        *Important* Strictly break only the Information/Summary (part) into multiple lines for better readability.
        In the end , provide a concise summary of the whole video in 2-3 lines.
        Here are the summaries:
        Summary 1: {summary1}
        Summary 2: {summary2}
        Keypoints/Topics: {topics}"""
        response = llm2.generate_content(prompt)
        if response:
            return {"messages": [AIMessage(content=response.text)]}
        else:
            return {"error_message": "Failed to generate summary comparison."}
        
    else:
        return {"error_message": "One or both summaries are missing. Cannot compare."}
    
def chatbot(State):
    """Simple Chatbot"""
    input_text = State.get("messages")
    if isinstance(input_text, list):
        input_text = input_text[-1].content
    response = llm2.generate_content(contents=f"""
                You are a helpful Teacher.
                Your task is to answer the user's question.
                Make sure to provide a concise and accurate response related to Studies and knowledge.
                Strictly stick to Studies and knowledge that are helpful to any student while keeping the previous inputs in memory.
                Here is the input: {input_text}""")
    return {"messages": response.text if response else "No response generated."}

def start_router(State):
    user_input = State.get("messages")
    if isinstance(user_input, list):
        user_input = user_input[-1].content
    #print("DEBUG: user_input =", repr(user_input))
    youtube_pattern = r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/"
    if user_input and re.search(youtube_pattern, user_input):
        #print("DEBUG: Routing to loader")
        return "transcript_loader"
    else:
        #print("DEBUG: Routing to chatbot")
        return "chatbot"

graph_builder=StateGraph(State)
#nodes
graph_builder.add_node("chatbot",chatbot)
graph_builder.add_node("transcript_loader", transcript_loader)
graph_builder.add_node("preprocessing", preprocess_transcript)
graph_builder.add_node("Keypoint_Extractor",keypoints)
graph_builder.add_node("writer", writer)
graph_builder.add_node("summary1", summary1)
graph_builder.add_node("summary2", summary2)
#edges
graph_builder.add_conditional_edges(START, start_router, {
    "transcript_loader": "transcript_loader",
    "chatbot": "chatbot"
})
graph_builder.add_edge("transcript_loader","preprocessing")
graph_builder.add_edge("preprocessing","Keypoint_Extractor")
graph_builder.add_edge("Keypoint_Extractor", "summary1")
graph_builder.add_edge("Keypoint_Extractor", "summary2")
graph_builder.add_edge("summary1", "writer")
graph_builder.add_edge("summary2", "writer")
graph_builder.add_edge("writer", END)
graph_builder.add_edge("chatbot", END)
graph=graph_builder.compile()

async def main():
    userinput = input("Enter the youtube video URL or your question: ")
    summary_length = input("Select Summary Length (short/medium/long): ").strip().lower()
    if summary_length not in ["short", "medium", "long"]:
        print("Invalid summary length. Defaulting to 'medium'.")
        summary_length = "medium"
    response_state = await graph.ainvoke({"messages": [HumanMessage(content=userinput)],"summary_length": summary_length})
    output = response_state["messages"][-1].content if "messages" in response_state else "No final output found."
    print("Final Response:")
    print(output)
    await asyncio.sleep(0.2)


if __name__ == "__main__":
    asyncio.run(main())
