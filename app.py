"""
AI Academic Assistant - Stable Version with Lazy Initialization

Architecture: RAG components load ONLY when needed.
- Streamlit starts instantly (no heavy imports at startup)
- Components initialize on-demand (upload, query, test)
- Full error handling with user feedback
- CPU-only mode (no GPU/CUDA)
"""

import os
import streamlit as st
import logging
from datetime import datetime
from typing import Optional, Dict, List

# ========== CRITICAL: FORCE CPU MODE ==========
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
# ============================================

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page config - MUST be first Streamlit command
st.set_page_config(
    page_title="AI Academic Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configure directories
UPLOAD_FOLDER = "uploads"
VECTORSTORE_FOLDER = "vectorstore"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(VECTORSTORE_FOLDER, exist_ok=True)

# Custom CSS
st.markdown("""
    <style>
    .main { padding: 2rem; }
    .success-box { background-color: #d4edda; padding: 1rem; border-radius: 0.5rem; }
    .source-box { background-color: #f0f2f6; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #1f77b4; }
    
    /* Job Matcher Styling */
    .match-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 1rem;
        text-align: center;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .skill-match {
        background-color: #d4edda;
        padding: 0.5rem;
        border-radius: 0.25rem;
        margin: 0.25rem 0;
        border-left: 3px solid #28a745;
    }
    
    .skill-missing {
        background-color: #f8d7da;
        padding: 0.5rem;
        border-radius: 0.25rem;
        margin: 0.25rem 0;
        border-left: 3px solid #dc3545;
    }
    
    .score-excellent {
        background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);
        color: #1a5f4a;
    }
    
    .score-good {
        background: linear-gradient(135deg, #feca57 0%, #ff9ff3 100%);
        color: #6c4c0f;
    }
    
    .score-needs-work {
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%);
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# ========== LAZY LOADING FUNCTIONS ==========
# These ONLY execute when explicitly called

@st.cache_resource
def load_embeddings_manager():
    """Lazy load embeddings (only when first needed)."""
    try:
        from utils.embeddings import EmbeddingsManager
        logger.info("Loading embeddings manager...")
        manager = EmbeddingsManager(model_name="all-MiniLM-L6-v2")
        logger.info("✅ Embeddings manager loaded")
        return manager
    except Exception as e:
        logger.error(f"❌ Error loading embeddings: {e}")
        st.error(f"❌ Embeddings Error: {e}")
        return None


@st.cache_resource
def load_rag_pipeline():
    """Lazy load RAG pipeline (only when first needed)."""
    try:
        from utils.rag_pipeline import RAGPipeline
        logger.info("Initializing RAG pipeline...")
        logger.info("Using Ollama model: tinyllama (CPU-optimized for stability)")
        
        pipeline = RAGPipeline(
            embeddings_model="all-MiniLM-L6-v2",
            llm_type="ollama",
            llm_model="tinyllama",  # Using tinyllama for stability
            vectorstore_path=VECTORSTORE_FOLDER
        )
        
        # Try to load existing FAISS index
        try:
            if pipeline.load_index():
                stats = pipeline.get_stats()
                st.success(f"✅ Loaded existing index with {stats['total_documents']} documents")
                logger.info(f"Loaded FAISS index with {stats['total_documents']} documents")
            else:
                st.info("📌 No existing index found. Upload documents to create one.")
                logger.info("No existing FAISS index found")
        except Exception as e:
            logger.warning(f"⚠️ Could not load FAISS index: {e}")
            st.warning(f"⚠️ FAISS Warning: {e}")
        
        logger.info("✅ RAG pipeline fully initialized with tinyllama")
        return pipeline
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Error loading RAG pipeline: {error_msg}")
        st.error(f"❌ RAG Pipeline Error: {error_msg}")
        logger.error("Make sure Ollama is running: ollama serve")
        logger.error("And tinyllama is available: ollama list")
        return None


def get_uploaded_files() -> List[str]:
    """Get list of uploaded PDFs."""
    if os.path.exists(UPLOAD_FOLDER):
        return [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.pdf')]
    return []


def process_pdf_to_rag(file_path: str, pipeline) -> Dict:
    """Process PDF: extract → chunk → embed → store."""
    try:
        from utils.pdf_reader import PDFReader
        from utils.text_splitter import TextSplitter
        
        logger.info(f"Processing PDF: {file_path}")
        
        # Step 1: Extract text
        pdf_reader = PDFReader()
        text, metadata = pdf_reader.extract_text_from_pdf(file_path)
        logger.info(f"✅ Extracted {len(text)} characters")
        
        # Step 2: Split into chunks
        splitter = TextSplitter(chunk_size=512, overlap=100)
        chunks = splitter.split_by_paragraphs(text)
        logger.info(f"✅ Created {len(chunks)} chunks")
        
        # Step 3: Create metadata
        chunk_metadata = [
            {
                "source": metadata.get("file_name", "unknown"),
                "page_count": metadata.get("total_pages", "?"),
                "chunk_index": i
            }
            for i in range(len(chunks))
        ]
        
        # Step 4: Add to RAG pipeline
        pipeline.add_documents(chunks, chunk_metadata)
        pipeline.save_index()
        logger.info(f"✅ Documents added to RAG pipeline")
        
        return {
            "success": True,
            "message": f"✅ Processed {metadata.get('file_name')}",
            "chunks": len(chunks),
            "file_size_kb": metadata.get("file_size_kb", 0)
        }
    
    except Exception as e:
        logger.error(f"❌ Error processing PDF: {e}")
        return {
            "success": False,
            "message": f"❌ Error: {str(e)}"
        }


# ========== MAIN UI ==========

st.markdown("# 📚 AI Academic Assistant")
st.markdown("*Your personalized RAG-powered academic learning companion*")

# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "rag_loaded" not in st.session_state:
    st.session_state.rag_loaded = False

if "resume_loaded" not in st.session_state:
    st.session_state.resume_loaded = False

if "resume_text" not in st.session_state:
    st.session_state.resume_text = ""

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

if "ats_result" not in st.session_state:
    st.session_state.ats_result = None

if "job_match_result" not in st.session_state:
    st.session_state.job_match_result = None

if "roadmap_result" not in st.session_state:
    st.session_state.roadmap_result = None

# Sidebar
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    
    # Status indicator
    if st.session_state.rag_loaded:
        st.success("✅ RAG Ready")
    else:
        st.info("⏳ RAG Not Loaded (will load on first use)")
    
    st.divider()
    
    # Tab selection
    tab = st.radio(
        "Navigation:",
        ["📝 Chat", "📤 Upload Documents", "📋 Resume Analyzer", "🎯 Job Matcher", "🚀 Career Roadmap", "📊 Info"],
        label_visibility="collapsed"
    )

# ========== TAB 1: CHAT ==========
if tab == "📝 Chat":
    st.markdown("## Ask Questions About Your Documents")
    
    uploaded_files = get_uploaded_files()
    
    if not uploaded_files:
        st.warning("📌 Please upload PDF documents first!")
        st.info("Go to **📤 Upload Documents** tab to get started.")
    else:
        # Load RAG only when user is in chat tab
        if not st.session_state.rag_loaded:
            with st.spinner("⏳ Loading RAG system..."):
                pipeline = load_rag_pipeline()
                if pipeline:
                    st.session_state.rag_loaded = True
                    st.session_state.pipeline = pipeline
                else:
                    st.error("❌ Failed to load RAG system")
                    st.stop()
        
        pipeline = st.session_state.pipeline
        stats = pipeline.get_stats()
        
        # Display documents count
        st.info(f"📚 Knowledge base: {stats['total_documents']} documents")
        
        # Display chat history
        st.markdown("### Conversation")
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.chat_message("user").write(message["content"])
            else:
                st.chat_message("assistant").write(message["content"])
        
        # Input area
        st.divider()
        
        col1, col2 = st.columns([0.85, 0.15])
        with col1:
            user_question = st.text_input(
                "Ask a question:",
                placeholder="E.g., What is deadlock in OS?",
                key="user_input"
            )
        
        with col2:
            submit_button = st.button("🚀 Ask", use_container_width=True)
        
        # Process question
        if submit_button and user_question:
            st.session_state.chat_history.append({
                "role": "user",
                "content": user_question
            })
            
            with st.spinner("🤔 Generating answer..."):
                try:
                    result = pipeline.generate_answer(
                        query=user_question,
                        top_k=5,
                        temperature=0.7
                    )
                    
                    answer = result["answer"]
                    confidence = result["confidence"]
                    sources = result["sources"]
                    
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": answer
                    })
                    
                    # Display answer
                    st.success("✅ Answer Generated!")
                    st.markdown("### Answer")
                    st.write(answer)
                    
                    # Display metrics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        confidence_pct = f"{confidence:.0%}"
                        st.metric("Confidence", confidence_pct)
                    with col2:
                        st.metric("Sources", result['retrieved_docs'])
                    
                    # Show sources
                    if sources:
                        st.markdown("### 📚 Sources")
                        unique_sources = list(set(sources))
                        for source in unique_sources:
                            st.markdown(f"<div class='source-box'>📄 {source}</div>", unsafe_allow_html=True)
                    
                    st.rerun()
                
                except Exception as e:
                    st.error(f"❌ Error generating answer: {str(e)}")
                    logger.error(f"Error: {e}")

# ========== TAB 2: UPLOAD ==========
elif tab == "📤 Upload Documents":
    st.markdown("## Upload Study Materials")
    
    col1, col2 = st.columns([0.6, 0.4])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Choose a PDF file:",
            type="pdf",
            accept_multiple_files=False
        )
        
        if uploaded_file is not None:
            # Save file
            file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            st.success(f"✅ Saved: {uploaded_file.name}")
            
            # Load RAG pipeline for processing
            with st.spinner("⏳ Loading RAG system..."):
                pipeline = load_rag_pipeline()
            
            if pipeline:
                # Process PDF
                with st.spinner("⚙️ Processing PDF..."):
                    result = process_pdf_to_rag(file_path, pipeline)
                
                if result["success"]:
                    st.success(result["message"])
                    st.info(f"📊 Created {result['chunks']} chunks")
                    st.balloons()
                    st.session_state.rag_loaded = True
                    st.session_state.pipeline = pipeline
                else:
                    st.error(result["message"])
            else:
                st.error("❌ Failed to load RAG system for processing")
    
    with col2:
        st.markdown("### 📋 Uploaded Files")
        files = get_uploaded_files()
        
        if files:
            for file in files:
                file_path = os.path.join(UPLOAD_FOLDER, file)
                file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                st.caption(f"📄 {file} ({file_size_mb:.2f} MB)")
        else:
            st.caption("No files uploaded yet")

# ========== TAB 3: RESUME ANALYZER ==========
elif tab == "📋 Resume Analyzer":
    st.markdown("## 📋 AI Resume Analyzer")
    st.markdown("*Get AI-powered feedback on your resume with ATS compatibility analysis*")
    
    resume_col1, resume_col2 = st.columns([0.6, 0.4])
    
    with resume_col1:
        st.markdown("### Upload Your Resume")
        resume_file = st.file_uploader(
            "Choose a resume PDF:",
            type="pdf",
            accept_multiple_files=False,
            key="resume_uploader"
        )
        
        if resume_file is not None:
            # Save resume temporarily
            temp_resume_path = os.path.join(UPLOAD_FOLDER, f"temp_{resume_file.name}")
            with open(temp_resume_path, "wb") as f:
                f.write(resume_file.getbuffer())
            
            st.success(f"✅ Loaded: {resume_file.name}")
            
            # Load RAG pipeline for analysis
            with st.spinner("⏳ Loading analysis engine..."):
                pipeline = load_rag_pipeline()
            
            if pipeline:
                # Extract resume text
                with st.spinner("📄 Extracting resume text..."):
                    try:
                        from utils.pdf_reader import PDFReader
                        pdf_reader = PDFReader()
                        resume_text, resume_metadata = pdf_reader.extract_text_from_pdf(temp_resume_path)
                        
                        st.session_state.resume_loaded = True
                        st.session_state.resume_text = resume_text
                        st.session_state.pipeline = pipeline
                        
                        st.success(f"✅ Extracted {len(resume_text)} characters")
                        
                    except Exception as e:
                        st.error(f"❌ Error extracting resume: {str(e)}")
                        st.session_state.resume_loaded = False
            else:
                st.error("❌ Failed to load analysis engine")
    
    with resume_col2:
        st.markdown("### Analysis Options")
        
        if "resume_loaded" in st.session_state and st.session_state.resume_loaded:
            analyze_button = st.button("🔍 Analyze Resume", use_container_width=True, key="analyze_btn")
            
            if analyze_button:
                pipeline = st.session_state.pipeline
                resume_text = st.session_state.resume_text
                
                with st.spinner("🤖 Analyzing resume with AI..."):
                    try:
                        # Get ATS score
                        ats_result = pipeline.calculate_ats_score(resume_text)
                        
                        # Get detailed analysis
                        analysis_result = pipeline.analyze_resume(resume_text)
                        
                        st.session_state.analysis_result = analysis_result
                        st.session_state.ats_result = ats_result
                        
                        if analysis_result["success"]:
                            st.success("✅ Analysis Complete!")
                        else:
                            st.error(f"❌ Analysis Error: {analysis_result.get('error', 'Unknown error')}")
                    
                    except Exception as e:
                        st.error(f"❌ Error during analysis: {str(e)}")
                        logger.error(f"Resume analysis error: {e}")
        else:
            st.info("📌 Upload a resume to get started")
    
    # Display analysis results
    analysis_result = st.session_state.analysis_result
    if (analysis_result is not None 
        and isinstance(analysis_result, dict) 
        and analysis_result.get("success", False)):
        st.divider()
        
        # ATS Score Card
        ats_data = st.session_state.ats_result
        ats_score = ats_data["ats_score"]
        
        # Color based on score
        if ats_score >= 80:
            color = "🟢"
        elif ats_score >= 60:
            color = "🟡"
        else:
            color = "🔴"
        
        col1, col2, col3 = st.columns([0.3, 0.4, 0.3])
        with col2:
            st.markdown(f"## {color} ATS Score: {ats_score}/100")
            st.markdown(f"*{ats_data['recommendation']}*")
        
        # Score breakdown
        with st.expander("📊 Score Breakdown"):
            breakdown = ats_data["score_breakdown"]
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Sections", f"{breakdown.get('sections', 0)}/25")
                st.metric("Keywords", f"{breakdown.get('keywords', 0)}/25")
            with col2:
                st.metric("Certifications", f"{breakdown.get('certifications', 0)}/15")
                st.metric("Metrics", f"{breakdown.get('metrics', 0)}/15")
            with col3:
                st.metric("Action Verbs", f"{breakdown.get('action_verbs', 0)}/10")
                st.metric("Formatting", f"{breakdown.get('formatting', 0)}/10")
            
            st.info(f"📝 Word Count: {ats_data['word_count']} (Optimal: 250-1000)")
        
        st.divider()
        
        # Detailed Analysis Sections
        analysis_sections = st.session_state.analysis_result.get("sections", {})
        
        # Define section order and emojis
        section_config = [
            ("Technical Skills", "🛠️"),
            ("Strengths", "⭐"),
            ("Weaknesses", "⚠️"),
            ("ATS Suggestions", "📌"),
            ("Career Recommendations", "🎯"),
            ("Learning Path", "📚"),
            ("Interview Tips", "🎤")
        ]
        
        # Display sections in tabs for better organization
        tabs = st.tabs([f"{emoji} {name}" for name, emoji in section_config])
        
        for (section_name, emoji), tab in zip(section_config, tabs):
            with tab:
                content = analysis_sections.get(section_name, "")
                if content:
                    st.markdown(content)
                else:
                    st.info(f"No {section_name.lower()} found in analysis")
        
        st.divider()
        
        # Suggested follow-up questions
        st.markdown("### 💡 Suggested Follow-up Questions")
        st.markdown("Ask the AI about your resume:")
        
        suggested_questions = [
            "What specific projects should I add to improve my resume?",
            "Which companies would be a good fit for this profile?",
            "How can I improve my ATS score by 10 points?",
            "Generate interview questions for this resume",
            "What should be my salary expectations based on this profile?",
            "How can I transition to a new role with this background?"
        ]
        
        col1, col2, col3 = st.columns(3)
        cols = [col1, col2, col3]
        
        for idx, question in enumerate(suggested_questions):
            col = cols[idx % 3]
            with col:
                if st.button(f"💬 {question}", use_container_width=True, key=f"q_{idx}"):
                    # Load RAG pipeline if not already loaded
                    if not st.session_state.get("rag_loaded", False):
                        with st.spinner("⏳ Loading RAG system..."):
                            pipeline = load_rag_pipeline()
                            st.session_state.pipeline = pipeline
                            if pipeline:
                                st.session_state.rag_loaded = True
                            else:
                                st.session_state.rag_loaded = False
                    
                    # Safe check: pipeline must exist and be loaded
                    pipeline = st.session_state.get("pipeline")
                    
                    if pipeline is None:
                        st.error("❌ RAG pipeline failed to load. Make sure Ollama is running with tinyllama model.")
                        logger.error(f"Pipeline is None when generating answer for: {question}")
                    else:
                        with st.spinner("🤔 Generating answer..."):
                            try:
                                logger.info(f"Processing follow-up question: {question}")
                                logger.info(f"Using model: tinyllama")
                                
                                # Include resume text in context for better answers
                                result = pipeline.generate_answer(
                                    query=f"Resume Context: {st.session_state.resume_text[:1000]}...\n\nQuestion: {question}",
                                    top_k=3,
                                    temperature=0.7
                                )
                                
                                if result and result.get("answer"):
                                    st.markdown(f"### Question: {question}")
                                    st.success("✅ Answer Generated:")
                                    st.markdown(result["answer"])
                                    logger.info(f"Successfully generated answer for: {question}")
                                else:
                                    st.warning("⚠️ No answer generated. Please try again.")
                                    logger.warning("Generated result was empty")
                                
                            except Exception as e:
                                error_msg = str(e)
                                logger.error(f"Error generating answer for '{question}': {error_msg}")
                                st.warning(f"⚠️ Could not generate answer at this moment.\n\nTip: Ensure Ollama is running with tinyllama model.\n\nError: {error_msg}")

# ========== TAB 4: JOB MATCHER ==========
elif tab == "🎯 Job Matcher":
    st.markdown("## 🎯 AI Job Description Matcher")
    st.markdown("*Compare your resume against any job description and get AI-powered improvement suggestions*")
    
    matcher_col1, matcher_col2 = st.columns([0.5, 0.5])
    
    with matcher_col1:
        st.markdown("### 📄 Upload Your Resume")
        job_resume_file = st.file_uploader(
            "Choose a resume PDF:",
            type="pdf",
            accept_multiple_files=False,
            key="job_matcher_resume"
        )
        
        job_matcher_resume_text = ""
        if job_resume_file is not None:
            temp_job_resume_path = os.path.join(UPLOAD_FOLDER, f"temp_jm_{job_resume_file.name}")
            with open(temp_job_resume_path, "wb") as f:
                f.write(job_resume_file.getbuffer())
            
            try:
                from utils.pdf_reader import PDFReader
                pdf_reader = PDFReader()
                job_matcher_resume_text, _ = pdf_reader.extract_text_from_pdf(temp_job_resume_path)
                st.success(f"✅ Loaded: {job_resume_file.name}")
            except Exception as e:
                st.error(f"❌ Error reading resume: {str(e)}")
    
    with matcher_col2:
        st.markdown("### 📋 Paste Job Description")
        job_description_text = st.text_area(
            "Paste the entire job description here:",
            height=200,
            placeholder="Paste job description from LinkedIn, Indeed, company website, etc.",
            key="job_description_input"
        )
    
    # Analyze button
    if job_matcher_resume_text and job_description_text:
        st.divider()
        
        if st.button("🚀 Analyze Match", use_container_width=True, key="analyze_job_match"):
            with st.spinner("🔍 Analyzing job match..."):
                try:
                    # Load pipeline
                    pipeline = load_rag_pipeline()
                    
                    if pipeline:
                        # Run job match analysis
                        match_result = pipeline.analyze_job_match(
                            resume_text=job_matcher_resume_text,
                            jd_text=job_description_text,
                            temperature=0.7
                        )
                        
                        if match_result["success"]:
                            st.session_state.job_match_result = match_result
                            st.success("✅ Analysis Complete!")
                        else:
                            st.error(f"❌ Analysis Error: {match_result.get('error', 'Unknown error')}")
                    else:
                        st.error("❌ Failed to load RAG pipeline")
                
                except Exception as e:
                    st.error(f"❌ Error during analysis: {str(e)}")
                    logger.error(f"Job match analysis error: {e}")
    
    # Display job match results
    # Safe check: key exists + value is not None + value is dict + success is True
    if (
        "job_match_result" in st.session_state
        and st.session_state.job_match_result is not None
        and isinstance(st.session_state.job_match_result, dict)
        and st.session_state.job_match_result.get("success", False)
    ):
        match_data = st.session_state.job_match_result
        match_pct = match_data.get("match_percentage", 0)
        
        st.divider()
        
        # ===== MATCH SCORE CARD =====
        if match_pct >= 75:
            color_indicator = "🟢"
            match_level = "Excellent"
        elif match_pct >= 50:
            color_indicator = "🟡"
            match_level = "Good"
        else:
            color_indicator = "🔴"
            match_level = "Needs Improvement"
        
        col1, col2, col3 = st.columns([0.3, 0.4, 0.3])
        with col2:
            st.markdown(f"## {color_indicator} Job Match Score: {match_pct:.1f}%")
            st.markdown(f"**Status:** *{match_level}*")
        
        st.divider()
        
        # ===== SKILLS COMPARISON =====
        skill_comp = match_data.get("skill_comparison", {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### ✅ Matching Skills")
            
            matching_tech = skill_comp.get("matching_technical", [])
            matching_soft = skill_comp.get("matching_soft", [])
            matching_certs = skill_comp.get("matching_certifications", [])
            
            if matching_tech:
                st.markdown("**Technical Skills:**")
                for skill in matching_tech:
                    st.markdown(f"✅ {skill}")
            
            if matching_soft:
                st.markdown("**Soft Skills:**")
                for skill in matching_soft:
                    st.markdown(f"✅ {skill}")
            
            if matching_certs:
                st.markdown("**Certifications:**")
                for cert in matching_certs:
                    st.markdown(f"✅ {cert}")
            
            if not (matching_tech or matching_soft or matching_certs):
                st.info("No matching skills found. Continue reading...")
        
        with col2:
            st.markdown("### ❌ Missing Skills")
            
            missing_tech = skill_comp.get("missing_technical", [])
            missing_soft = skill_comp.get("missing_soft", [])
            missing_certs = skill_comp.get("missing_certifications", [])
            
            if missing_tech:
                st.markdown("**Technical Skills:**")
                for skill in missing_tech[:5]:
                    st.markdown(f"❌ {skill}")
                if len(missing_tech) > 5:
                    st.caption(f"... and {len(missing_tech) - 5} more")
            
            if missing_soft:
                st.markdown("**Soft Skills:**")
                for skill in missing_soft[:3]:
                    st.markdown(f"❌ {skill}")
                if len(missing_soft) > 3:
                    st.caption(f"... and {len(missing_soft) - 3} more")
            
            if missing_certs:
                st.markdown("**Certifications:**")
                for cert in missing_certs:
                    st.markdown(f"❌ {cert}")
            
            if not (missing_tech or missing_soft or missing_certs):
                st.success("✅ All key skills are present!")
        
        st.divider()
        
        # ===== AI RECOMMENDATIONS =====
        rec_data = match_data.get("recommendations", {})
        if rec_data.get("success"):
            rec_sections = rec_data.get("sections", {})
            
            st.markdown("### 🤖 AI Recommendations")
            
            # Create tabs for recommendations
            rec_tabs = st.tabs([
                "💡 Improvements",
                "🛠️ Projects",
                "📜 Certifications",
                "📝 Resume Tips",
                "📊 Hiring Outlook"
            ])
            
            with rec_tabs[0]:
                content = rec_sections.get("Improvement Suggestions", "")
                if content:
                    st.markdown(content)
                else:
                    st.info("No specific improvements identified")
            
            with rec_tabs[1]:
                content = rec_sections.get("Recommended Projects", "")
                if content:
                    st.markdown(content)
                else:
                    st.info("No specific projects recommended")
            
            with rec_tabs[2]:
                content = rec_sections.get("Recommended Certifications", "")
                if content:
                    st.markdown(content)
                else:
                    st.info("No specific certifications recommended")
            
            with rec_tabs[3]:
                content = rec_sections.get("Resume Optimization", "")
                if content:
                    st.markdown(content)
                else:
                    st.info("No specific optimization tips")
            
            with rec_tabs[4]:
                content = rec_sections.get("Hiring Probability", "")
                if content:
                    st.markdown(content)
                else:
                    st.info("No hiring assessment available")
        
        st.divider()
        
        # ===== FOLLOW-UP QUESTIONS =====
        st.markdown("### 💬 Follow-up Smart Questions")
        st.markdown("Ask the AI for more help:")
        
        followup_questions = [
            "What projects should I build to improve this match?",
            "Generate interview questions for this job description",
            "How can I rewrite my resume for this specific role?",
            "What certifications should I prioritize?",
            "Create a 3-month learning plan to land this job",
            "What companies hire for similar roles?"
        ]
        
        col1, col2, col3 = st.columns(3)
        cols = [col1, col2, col3]
        
        for idx, question in enumerate(followup_questions):
            col = cols[idx % 3]
            with col:
                if st.button(f"❓ {question}", use_container_width=True, key=f"jm_q_{idx}"):
                    # Load RAG pipeline if not already loaded
                    if not st.session_state.get("rag_loaded", False):
                        with st.spinner("⏳ Loading RAG system..."):
                            pipeline = load_rag_pipeline()
                            st.session_state.pipeline = pipeline
                            if pipeline:
                                st.session_state.rag_loaded = True
                            else:
                                st.session_state.rag_loaded = False
                    
                    # Safe check: pipeline must exist and be loaded
                    pipeline = st.session_state.get("pipeline")
                    
                    if pipeline is None:
                        st.error("❌ RAG pipeline failed to load. Make sure Ollama is running with tinyllama model.")
                        logger.error(f"Pipeline is None when generating answer for Job Matcher: {question}")
                    else:
                        with st.spinner("🤔 Generating answer..."):
                            try:
                                logger.info(f"Processing Job Matcher follow-up: {question}")
                                logger.info(f"Using model: tinyllama")
                                
                                # Include job context for better answers
                                context_prompt = f"""
Job Description Context:
{job_description_text[:1500]}

Resume Match Score: {match_pct:.1f}%

User Question: {question}
"""
                                
                                result = pipeline.generate_answer(
                                    query=context_prompt,
                                    top_k=3,
                                    temperature=0.7
                                )
                                
                                if result and result.get("answer"):
                                    st.markdown(f"### Question: {question}")
                                    st.success("✅ Answer Generated:")
                                    st.markdown(result["answer"])
                                    logger.info(f"Successfully generated answer for Job Matcher: {question}")
                                else:
                                    st.warning("⚠️ No answer generated. Please try again.")
                                    logger.warning("Job Matcher generated result was empty")
                                
                            except Exception as e:
                                error_msg = str(e)
                                logger.error(f"Error generating Job Matcher answer for '{question}': {error_msg}")
                                st.warning(f"⚠️ Could not generate answer at this moment.\n\nTip: Ensure Ollama is running with tinyllama model.\n\nError: {error_msg}")
    
    elif job_matcher_resume_text and job_description_text:
        st.info("📌 Click 'Analyze Match' to begin the analysis")
    elif not job_matcher_resume_text and not job_description_text:
        st.info("📌 Upload a resume and paste a job description to get started")
    else:
        st.warning("📌 Please provide both resume and job description")

# ========== TAB 6: CAREER ROADMAP GENERATOR ==========
elif tab == "🚀 Career Roadmap":
    st.markdown("## 🚀 AI Career Roadmap Generator")
    st.markdown("*Generate a personalized career development plan based on your resume and goals*")
    st.info("✅ Career Roadmap page loaded successfully.")

    roadmap_resume_text = ""
    roadmap_resume_file = st.file_uploader(
        "Upload your resume PDF or DOCX:",
        type=["pdf", "docx"],
        key="roadmap_resume"
    )

    if roadmap_resume_file is not None:
        try:
            from utils.pdf_reader import PDFReader
            pdf_reader = PDFReader()
            temp_roadmap_path = os.path.join(UPLOAD_FOLDER, f"temp_roadmap_{roadmap_resume_file.name}")
            with open(temp_roadmap_path, "wb") as f:
                f.write(roadmap_resume_file.getbuffer())

            roadmap_resume_text, _ = pdf_reader.extract_text_from_pdf(temp_roadmap_path)
            st.success(f"✅ Loaded: {roadmap_resume_file.name}")
        except Exception as e:
            st.error(f"❌ Error reading resume: {str(e)}")

    career_goal = st.selectbox(
        "Select your target role:",
        [
            "AI Engineer",
            "Machine Learning Engineer",
            "Data Scientist",
            "Computer Vision Engineer",
            "Generative AI Engineer",
            "Software Developer",
            "Full Stack Developer",
            "Research Engineer",
            "AI Product Engineer"
        ],
        key="career_goal"
    )

    experience_level = st.radio(
        "Current experience level:",
        ["Beginner", "Intermediate", "Advanced"],
        key="exp_level",
        horizontal=True
    )

    timeline = st.selectbox(
        "Timeline:",
        ["30 Days", "3 Months", "6 Months", "1 Year"],
        key="timeline"
    )

    if st.button("🚀 Generate AI Roadmap", use_container_width=True, key="gen_roadmap"):
        if not roadmap_resume_text:
            st.warning("📌 Please upload your resume first.")
        else:
            with st.spinner("🤖 Generating your personalized AI career roadmap..."):
                try:
                    pipeline = load_rag_pipeline()
                    if pipeline is None:
                        st.error("❌ Failed to load RAG pipeline. Please ensure Ollama is running with tinyllama.")
                    else:
                        roadmap_result = pipeline.generate_career_roadmap(
                            resume_text=roadmap_resume_text,
                            career_goal=career_goal,
                            experience_level=experience_level,
                            timeline=timeline,
                            temperature=0.7
                        )
                        if roadmap_result and roadmap_result.get("success"):
                            st.session_state.roadmap_result = roadmap_result
                            st.success("✅ Roadmap generated successfully.")
                        else:
                            st.error(f"❌ Could not generate roadmap: {roadmap_result.get('error', 'Unknown error')}")
                except Exception as e:
                    logger.error(f"Roadmap generation exception: {e}")
                    st.error(f"❌ Roadmap generation failed: {e}")

    st.divider()

    if (
        "roadmap_result" in st.session_state
        and st.session_state.roadmap_result
    ):
        roadmap_data = st.session_state.roadmap_result

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🎯 Target Role", roadmap_data.get("career_goal", "N/A"))
        with col2:
            st.metric("📊 Experience", roadmap_data.get("experience_level", "N/A"))
        with col3:
            st.metric("⏱️ Timeline", roadmap_data.get("timeline", "N/A"))
        with col4:
            st.metric("Status", "Ready")

        st.divider()

        st.write(roadmap_data)

        roadmap_sections = roadmap_data.get("sections", {})
        roadmap_full = roadmap_data.get("full_roadmap", "")
        section_list = [
            "Career Goal",
            "Skill Analysis",
            "Learning Roadmap",
            "Recommended Projects",
            "Learning Resources",
            "Interview Preparation",
            "Career Strategy",
            "Key Milestones"
        ]

        roadmap_tabs = st.tabs([f"📖 {sec}" for sec in section_list])
        for section_name, tab in zip(section_list, roadmap_tabs):
            with tab:
                with st.expander(section_name, expanded=True):
                    content = roadmap_sections.get(section_name, "") or ""
                    if content:
                        st.markdown(content)
                    elif roadmap_full:
                        st.info(f"No structured content found for {section_name}. Showing raw generated roadmap instead.")
                        st.markdown(roadmap_full)
                    else:
                        st.info(f"No content available for {section_name} yet.")

        st.divider()

        st.markdown("### 💡 Ask Follow-up Questions")
        st.markdown("Get more details about your personalized roadmap:")

        followup_questions = [
            "What projects should I build first to land this role?",
            "Which certifications are most important for this career path?",
            "How do I prepare for interviews in this field?",
            "What GitHub projects improve my profile most?",
            "How can I find internships faster in this domain?",
            "What learning resources are best for my level?"
        ]

        cols = st.columns(3)
        for idx, question in enumerate(followup_questions):
            with cols[idx % 3]:
                if st.button(f"❓ {question}", use_container_width=True, key=f"roadmap_q_{idx}"):
                    if not st.session_state.get("rag_loaded", False):
                        with st.spinner("⏳ Loading RAG system..."):
                            pipeline = load_rag_pipeline()
                            st.session_state.pipeline = pipeline
                            st.session_state.rag_loaded = pipeline is not None

                    pipeline = st.session_state.get("pipeline")
                    if pipeline is None:
                        st.error("❌ RAG pipeline failed to load. Make sure Ollama is running with tinyllama model.")
                        logger.error(f"Pipeline is None when generating roadmap follow-up answer: {question}")
                    else:
                        with st.spinner("🤔 Generating follow-up advice..."):
                            try:
                                context_prompt = f"""
Career Goal: {roadmap_data.get('career_goal')}
Experience Level: {roadmap_data.get('experience_level')}
Timeline: {roadmap_data.get('timeline')}

User Question: {question}

Provide specific, actionable advice for this career roadmap.
"""
                                result = pipeline.generate_answer(
                                    query=context_prompt,
                                    top_k=3,
                                    temperature=0.7
                                )
                                if result and result.get("answer"):
                                    st.markdown(f"### Question: {question}")
                                    st.success("✅ Answer Generated:")
                                    st.markdown(result["answer"])
                                else:
                                    st.warning("⚠️ No answer generated. Please try again.")
                            except Exception as e:
                                logger.error(f"Roadmap follow-up exception: {e}")
                                st.warning(f"⚠️ Could not generate answer at this moment.\n\nError: {e}")

# ========== TAB 7: INFO ==========
elif tab == "📊 Info":
    st.markdown("## 📊 System Information")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("CPU Mode", "✅ Enabled")
    with col2:
        st.metric("CUDA", "❌ Disabled")
    with col3:
        st.metric("Files Uploaded", len(get_uploaded_files()))
    
    st.divider()
    
    st.markdown("### 🧠 RAG Architecture")
    st.write("""
    **Pipeline Components:**
    1. **PDF Reader** - Extract text from PDFs
    2. **Text Splitter** - Chunk text with overlap
    3. **Embeddings** - Sentence Transformers (CPU mode)
    4. **FAISS** - Vector similarity search
    5. **LLM** - Ollama Llama3 (local)
    
    **Processing Flow:**
    PDF → Extract → Chunk → Embed → FAISS → Retrieve → LLM → Answer
    """)
    
    st.divider()
    
    st.markdown("### 🛠️ Troubleshooting")
    
    if st.button("🔄 Clear All Data"):
        import shutil
        if os.path.exists(UPLOAD_FOLDER):
            shutil.rmtree(UPLOAD_FOLDER)
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        if os.path.exists(VECTORSTORE_FOLDER):
            shutil.rmtree(VECTORSTORE_FOLDER)
            os.makedirs(VECTORSTORE_FOLDER, exist_ok=True)
        st.session_state.chat_history = []
        st.session_state.rag_loaded = False
        st.success("✅ All data cleared")
        st.rerun()
    
    if st.button("🧪 Test Components"):
        st.info("Testing embeddings...")
        emb = load_embeddings_manager()
        if emb:
            test_embedding = emb.generate_single_embedding("test")
            st.success(f"✅ Embeddings working (dimension: {len(test_embedding)})")
        
        st.info("Testing RAG pipeline...")
        pipeline = load_rag_pipeline()
        if pipeline:
            stats = pipeline.get_stats()
            st.success(f"✅ RAG pipeline working ({stats['total_documents']} docs)")
