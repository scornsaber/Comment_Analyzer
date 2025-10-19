import os
import streamlit as st
import pandas as pd
from pytubefix import YouTube,extract
from fetch_youtube import extract_video_id, fetch_comments
from analyze import analyze
from datetime import date
from numpy.random import default_rng as rng
import plotly.graph_objects as go
import plotly.figure_factory as ff
import plotly.express as px
#Comment summary

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import TextLoader, CSVLoader
from langchain_text_splitters import CharacterTextSplitter
#from dotenv import load_dotenv

#pip install langchain_llm
#pip install langchain_community 
#pip install langchain_groq



current_date = (date.today()).strftime("%m/%d/%Y")
st.set_page_config(page_title="YouTube Comment Analyzer", layout="wide")
st.title("YouTube Comment Analyzer")

#Use API key from secrets.toml or env var
api_key = st.secrets.get("YOUTUBE_API_KEY") or os.getenv("YOUTUBE_API_KEY", "")
grok_api_key= st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY","")

url = st.text_input("YouTube URL or Video ID")

if not api_key:
    st.warning("No YouTube API key set. Add it in .streamlit/secrets.toml or as env var YOUTUBE_API_KEY.")

if st.button("Analyze") and url and api_key:
    video_id = extract_video_id(url)
    video_title = YouTube(url).title
    video_date = YouTube(url).publish_date
    video_description = YouTube(url).description
    
    

    with st.spinner(f"Fetching comments from {video_title} ..."):
        df = fetch_comments(video_id, api_key, max_pages=5)
    with st.spinner("Analyzing…"):
        result = analyze(df)

    st.subheader(f"Summary from: {video_title} as of {current_date}")
    st.metric("Comments fetched", result["scalars"]["n_comments"])
    st.metric("Avg. text length", f"{result['scalars']['avg_text_len']:.1f}")

    st.subheader("Sample comments")
    st.dataframe(df.head(200))

    st.subheader("Downloads")
    st.download_button(
        "Download comments (CSV)",
        df.to_csv(index=False).encode("utf-8"),
        file_name=f" ({video_title})({video_id}) ({current_date})_comments.csv",
        mime="text/csv"
    )

    st.download_button(
        f"Download analysis(JSON)",
        pd.Series(result).to_json(indent=2).encode("utf-8"),
        file_name=f"{video_title}({video_id})({current_date})_analysis.json",
        mime="application/json"
    )

    initial_sidebar_state="collapsed"

    with st.expander("View Comment Summary"):
        st.title("#Comment Summary")
        st.write("Summary")
        st.write("From the video the general summary is as follows: ")
        st.write("Summary goes here...")
        st.write(f"Generated on {current_date}")

    with st.expander("View Comment Sentiment Analysis"):
        st.title("#Sentiment Analysis")
        st.write("Sentiment Analysis")
        st.write("From the video the general sentiment is as follows: ")
        st.write("Sentiment goes here...")
        st.write(f"Generated on {current_date}")


    with st.expander("View Dashboards"):

        #bar chart example
        df = pd.DataFrame(rng(0).standard_normal((20, 3)), columns=["a", "b", "c"])
        st.bar_chart(df)

        #line chart
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=[1, 2, 3, 4, 5],
                y=[1, 3, 2, 5, 4]
            )
        )
        st.plotly_chart(fig, config = {'scrollZoom': True})

        #scatter chart 
        df = px.data.iris()
        fig = px.scatter(df, x="sepal_width", y="sepal_length")
        event = st.plotly_chart(fig, key="iris", on_select="rerun")
#End of dashboard reading 



#comment summary stuff 



#load_dotenv() #allows reading of API keys
commentFile= st.file_uploader("Upload the directory of the CSV file of the comments", type = ["txt", "csv"])

llm=ChatGroq(model="openai/gpt-oss-120b")


parser = StrOutputParser()
prompt_template = ChatPromptTemplate.from_template("Make a summary of the collective topics from the comments in: {document}")


#chain
chain = prompt_template | llm | parser
if commentFile is not None: 
    with st.spinner("Processing"):
        try: 
            temp_FilePath=commentFile.name
            with open (temp_FilePath, "wb") as f:
              f.write(commentFile.getbuffer())
            if commentFile.type == "text/csv": 
            
                loader= CSVLoader(temp_FilePath, encoding='utf-8')
            else: 
                st.error("Only CSV files are supported")
                st.stop() 
                
            doc=loader.load()
            result = chain.invoke({"document": doc})

            #text splitting

            text_splitter = CharacterTextSplitter(chunk_size=100, chunk_overlap=10)
            chunks = text_splitter.split_documents(doc)
            

        except Exception as e: 
            print(e)
            st.error("Error processing document.")
            st.stop()
        st.success("File uploaded and broken into chunks. ")

#chunk summarization 
chunk_summaries = []
if st.button("Summarize"):
    
    with st.spinner ("Summarizing comments..."):
        try:
                for chunk in chunks: 
                    #Tell AI how to summarize the comment section
                      chunk_prompt = ChatPromptTemplate.from_template(
                      f"The text from this document comes from a YouTube comment section"
                      "Summarize the comments from this text with respect to frequent topics and general sentiment."
                      "Highlight the most critical information, and prioritize comments with the most amount of likes: \n\n {document}"
                          )
                      chunk_chain = chunk_prompt |llm | parser 
                      chunk_chain.invoke({"document": chunk})
                      chunk_summary = chunk_chain.invoke({"document": chunk})
                      chunk_summaries.append(chunk_summary)
                      #print ("Summaries", chunk_summary)
        except Exception as e: 
             print(e)
             st.error("Error processing chunks.")
             st.stop()
        st.success("Chunks processed ")

    with st.spinner("Final Summary"):
        try: 
            combined_summaries = "\n". join(chunk_summaries)

            final_prompt = ChatPromptTemplate.from_template(
                          "The text from this document comes from a YouTube comment section"
                          "Summarize the comments from this text with respect to frequent topics and general sentiment."
                          "Highlight the most critical information, and prioritize comments with the most amount of likes. Keep this under half a page long: \n\n {document}"
                              )
            final_chain = final_prompt|llm|parser
            final_summary = final_chain.invoke({"document": combined_summaries})
            st.write(f"Summary: {final_summary}")
            #print ("FINAL SUMMARY", final_summary)
        except Exception as e: 
            print(e)
            st.error("Error processing summary.")
            st.stop()
        st.success("Summary processed.")



    #st.link_button("View Dashboards", url="/Dashboard") 
    #st.link_button("View Comment Summary", url="/Summary") 
    #st.link_button("View Sentiment Analysis", url="/Sentiment") 
