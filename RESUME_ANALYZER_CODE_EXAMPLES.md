# 💻 Resume Analyzer - Code Examples & API Reference

## Overview
This document provides code examples and API reference for the new resume analyzer feature.

---

## Python API Examples

### Basic Usage in Your Code

#### Example 1: Analyze a Resume
```python
from utils.rag_pipeline import RAGPipeline
from utils.pdf_reader import PDFReader

# Initialize
pipeline = RAGPipeline(
    embeddings_model="all-MiniLM-L6-v2",
    llm_type="ollama",
    llm_model="tinyllama",
    vectorstore_path="./vectorstore"
)

# Extract resume text
pdf_reader = PDFReader()
resume_text, metadata = pdf_reader.extract_text_from_pdf("resume.pdf")

# Analyze resume
result = pipeline.analyze_resume(resume_text, temperature=0.7)

if result["success"]:
    print("Analysis Sections:")
    for section_name, content in result["sections"].items():
        print(f"\n{section_name}:")
        print(content)
else:
    print(f"Error: {result['error']}")
```

#### Example 2: Get ATS Score
```python
# Calculate ATS score
ats_result = pipeline.calculate_ats_score(resume_text)

print(f"ATS Score: {ats_result['ats_score']}/100")
print(f"Recommendation: {ats_result['recommendation']}")
print(f"Word Count: {ats_result['word_count']}")

# View breakdown
breakdown = ats_result['score_breakdown']
print(f"\nScore Breakdown:")
print(f"  Sections: {breakdown['sections']}/25")
print(f"  Keywords: {breakdown['keywords']}/25")
print(f"  Certifications: {breakdown['certifications']}/15")
print(f"  Metrics: {breakdown['metrics']}/15")
print(f"  Action Verbs: {breakdown['action_verbs']}/10")
print(f"  Formatting: {breakdown['formatting']}/10")
```

#### Example 3: Complete Analysis Pipeline
```python
def full_resume_analysis(resume_path: str, pipeline: RAGPipeline) -> dict:
    """Complete resume analysis workflow."""
    
    # Step 1: Extract text
    pdf_reader = PDFReader()
    resume_text, metadata = pdf_reader.extract_text_from_pdf(resume_path)
    
    # Step 2: Calculate ATS score
    ats_score = pipeline.calculate_ats_score(resume_text)
    
    # Step 3: Get detailed analysis
    analysis = pipeline.analyze_resume(resume_text)
    
    # Step 4: Compile results
    results = {
        "ats_score": ats_score["ats_score"],
        "recommendation": ats_score["recommendation"],
        "analysis_sections": analysis["sections"],
        "word_count": ats_score["word_count"],
        "score_breakdown": ats_score["score_breakdown"]
    }
    
    return results

# Usage
results = full_resume_analysis("my_resume.pdf", pipeline)
print(f"Overall ATS Score: {results['ats_score']}/100")
```

---

## API Reference

### `RAGPipeline.analyze_resume()`

```python
def analyze_resume(
    self, 
    resume_text: str, 
    temperature: float = 0.7
) -> Dict:
    """
    Analyze resume using LLM with structured prompt.
    
    Args:
        resume_text: Extracted resume text
        temperature: Temperature for LLM generation (0.0-1.0)
                    Higher = more creative, lower = more focused
    
    Returns:
        {
            "success": bool,                    # Analysis succeeded
            "full_analysis": str,               # Complete LLM response
            "sections": {                       # Parsed sections
                "Technical Skills": str,
                "Strengths": str,
                "Weaknesses": str,
                "ATS Suggestions": str,
                "Career Recommendations": str,
                "Learning Path": str,
                "Interview Tips": str
            },
            "resume_length_chars": int         # Input length
        }
    """
```

**Example**:
```python
result = pipeline.analyze_resume(
    resume_text="Python Developer with 5 years...",
    temperature=0.5  # More consistent output
)

if result["success"]:
    print(result["sections"]["Technical Skills"])
```

---

### `RAGPipeline.calculate_ats_score()`

```python
def calculate_ats_score(self, resume_text: str) -> Dict:
    """
    Calculate ATS compatibility score (0-100).
    
    Args:
        resume_text: Resume text to analyze
    
    Returns:
        {
            "ats_score": int,                   # 0-100
            "score_breakdown": {
                "sections": int,                # 0-25
                "keywords": int,                # 0-25
                "certifications": int,          # 0-15
                "metrics": int,                 # 0-15
                "action_verbs": int,            # 0-10
                "formatting": int               # 0-10
            },
            "word_count": int,                  # Resume length
            "recommendation": str               # Human-readable feedback
        }
    """
```

**Example**:
```python
ats = pipeline.calculate_ats_score(resume_text)
print(f"Score: {ats['ats_score']}/100")
print(f"Status: {ats['recommendation']}")

# Access individual scores
if ats['score_breakdown']['keywords'] < 10:
    print("Add more technical keywords to your resume")
```

---

## Streamlit Integration Examples

### How It's Used in app.py

#### Resume Upload
```python
resume_file = st.file_uploader(
    "Choose a resume PDF:",
    type="pdf",
    accept_multiple_files=False
)

if resume_file is not None:
    # Save and extract
    with open(temp_path, "wb") as f:
        f.write(resume_file.getbuffer())
    
    pdf_reader = PDFReader()
    resume_text, _ = pdf_reader.extract_text_from_pdf(temp_path)
    st.session_state.resume_text = resume_text
```

#### Display Analysis Results
```python
# Show ATS score
st.metric("ATS Score", f"{ats_score}/100")

# Show breakdown
cols = st.columns(3)
with cols[0]:
    st.metric("Keywords", breakdown['keywords'])
    
# Display sections in tabs
tabs = st.tabs(["Skills", "Strengths", "Weaknesses"])
with tabs[0]:
    st.write(sections["Technical Skills"])
```

#### Interactive Follow-up Questions
```python
if st.button("What projects should I add?"):
    result = pipeline.generate_answer(
        query="What projects would improve this resume?",
        top_k=3
    )
    st.write(result["answer"])
```

---

## Customization Examples

### Modifying the Analysis Prompt

In `utils/rag_pipeline.py`, find the `analyze_resume()` method:

```python
# Current prompt structure
analysis_prompt = f"""You are an expert ATS reviewer...

Analyze the following resume and provide:

1. Technical Skills Summary
2. Candidate Strengths
...

Resume:
{resume_text}"""

# To customize:
analysis_prompt = f"""You are a hiring manager for [SPECIFIC COMPANY]...

Analyze this resume for [SPECIFIC ROLE]:

1. Tech Stack Match
2. Experience Level
...
"""
```

### Adjusting ATS Score Weights

In `calculate_ats_score()` method:

```python
# Change point distribution
# Example: Increase keyword importance from 25 to 35
keyword_score = min(35, keywords_found * 2)  # Changed from 25

# Or adjust multipliers
keyword_score = min(25, keywords_found * 3)  # More keywords = higher score
```

### Customizing Recommendations

In `_get_ats_recommendation()` method:

```python
def _get_ats_recommendation(self, score: int) -> str:
    if score >= 90:
        return "🏆 Perfect! This is an exemplary resume."
    elif score >= 80:
        return "✅ Excellent! Industry-leading ATS optimization."
    # ... etc
```

---

## Error Handling Examples

### Catching Analysis Errors

```python
try:
    result = pipeline.analyze_resume(resume_text)
    if result["success"]:
        process_results(result["sections"])
    else:
        logger.error(f"Analysis failed: {result['error']}")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    st.error("Resume analysis failed. Please try again.")
```

### Handling ATS Score Edge Cases

```python
ats_result = pipeline.calculate_ats_score(resume_text)

# Check word count
if ats_result['word_count'] < 250:
    st.warning("Resume is quite short (< 250 words)")
elif ats_result['word_count'] > 1500:
    st.info("Resume is long (> 1500 words), consider condensing")

# Check scores
breakdown = ats_result['score_breakdown']
if breakdown['keywords'] == 0:
    st.warning("No technical keywords detected. Add your skills!")
```

---

## Performance Tips

### 1. Cache Analysis Results
```python
import streamlit as st

@st.cache_resource
def get_analysis(resume_text):
    result = pipeline.analyze_resume(resume_text)
    return result

# Only re-runs if resume_text changes
analysis = get_analysis(st.session_state.resume_text)
```

### 2. Optimize for Speed
```python
# Use lower temperature for faster, more consistent output
result = pipeline.analyze_resume(resume_text, temperature=0.3)
```

### 3. Batch Multiple Resumes
```python
import concurrent.futures

def analyze_batch(resumes: List[str]) -> List[Dict]:
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(pipeline.analyze_resume, resumes)
    return list(results)
```

---

## Advanced Usage

### Custom Analysis Sections

Create custom analysis by modifying the prompt:

```python
def custom_resume_analysis(resume_text: str, focus: str):
    """Analyze resume with custom focus."""
    
    custom_prompt = f"""
    Focus: {focus}
    
    Analyze this resume for:
    1. Relevance to {focus}
    2. Key transferable skills
    3. Gaps for {focus}
    4. How to pivot to {focus}
    
    Resume: {resume_text}
    """
    
    return pipeline.llm.generate(custom_prompt)
```

### Comparing Multiple Resumes

```python
def compare_resumes(resume1: str, resume2: str) -> Dict:
    """Compare two resumes."""
    
    ats1 = pipeline.calculate_ats_score(resume1)
    ats2 = pipeline.calculate_ats_score(resume2)
    
    return {
        "resume1_score": ats1['ats_score'],
        "resume2_score": ats2['ats_score'],
        "difference": ats1['ats_score'] - ats2['ats_score'],
        "winner": "Resume 1" if ats1['ats_score'] > ats2['ats_score'] else "Resume 2"
    }
```

### Generate Role-Specific Feedback

```python
def role_specific_analysis(resume_text: str, target_role: str):
    """Analyze resume for specific role."""
    
    custom_query = f"""
    This candidate is applying for: {target_role}
    
    Resume:
    {resume_text}
    
    Provide:
    1. How well matched are they?
    2. Missing skills
    3. Relevant projects they have
    4. 5 interview questions
    """
    
    return pipeline.llm.generate(custom_query)
```

---

## Data Flow Diagram

```
User uploads PDF
        ↓
PDF Reader extracts text
        ↓
Text stored in session state
        ↓
User clicks "Analyze"
        ↓
┌─────────────────────────┐
├─ ATS Score calculated   │
├─ AI analysis generated  │
├─ Results parsed         │
└─────────────────────────┘
        ↓
Results displayed in tabs
        ↓
User can ask follow-up questions
        ↓
RAG pipeline answers using context
```

---

## Testing & Debugging

### Debug Mode

Add to app.py for development:

```python
if st.checkbox("🔧 Debug Mode"):
    st.write("Session State:")
    st.write(st.session_state)
    
    if st.session_state.get("resume_text"):
        st.write(f"Resume Length: {len(st.session_state.resume_text)} chars")
    
    if st.session_state.get("analysis_result"):
        st.write("Analysis Status:", st.session_state.analysis_result.get("success"))
```

### Sample Test Resume

Create a test with known characteristics:

```python
test_resume = """
John Doe
john@example.com | linkedin.com/in/johndoe

TECHNICAL SKILLS
Python, JavaScript, React, Node.js, AWS, Docker, PostgreSQL, MongoDB

EXPERIENCE
Senior Software Engineer - Tech Company (2020-Present)
- Developed microservices using Python and Docker
- Led team of 5 engineers
- Improved performance by 40%

EDUCATION
BS Computer Science - University Name

CERTIFICATIONS
AWS Certified Solutions Architect
"""

# Test analysis
result = pipeline.analyze_resume(test_resume)
assert result["success"] == True
assert len(result["sections"]) == 7
```

---

## Troubleshooting

### Issue: Analysis Takes Too Long
```python
# Use faster model if available
pipeline = RAGPipeline(
    llm_model="tinyllama"  # Faster
)

# Or adjust temperature for speed
result = pipeline.analyze_resume(resume_text, temperature=0.3)
```

### Issue: ATS Score Seems Wrong
```python
# Check breakdown
ats = pipeline.calculate_ats_score(resume_text)
print(ats['score_breakdown'])
print(f"Word count: {ats['word_count']}")

# If word count is low:
if ats['word_count'] < 250:
    print("Resume too short - add more details")
```

### Issue: Missing Sections in Analysis
```python
# Check if parsing worked
result = pipeline.analyze_resume(resume_text)
print("Sections found:", len(result['sections']))
print("Missing:", [k for k, v in result['sections'].items() if not v])
```

---

**Last Updated**: 2026-05-21
**Version**: 1.0
**Ready for Production**: ✅

