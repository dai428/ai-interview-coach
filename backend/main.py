"""FastAPI — AI Interview Coach"""
import os, uuid
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import config
from interview_engine import new_id, analyze, score_answer, get_questions, get_answers, get_report, generate_resume_and_tech

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"AI Interview Coach: http://localhost:8008")
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def extract_text_from_docx(file_path):
    try:
        from docx import Document
        doc = Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        print(f"Error reading DOCX: {e}")
        return ""

def extract_text_from_pdf(file_path):
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""

def extract_text_from_image(file_path):
    try:
        import easyocr
        reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
        result = reader.readtext(file_path, detail=0)
        return "\n".join(result)
    except Exception as e:
        print(f"Error reading image: {e}")
        return ""

def process_resume_file(file: UploadFile) -> str:
    file_ext = file.filename.split('.')[-1].lower()
    file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}.{file_ext}")
    
    with open(file_path, "wb") as f:
        f.write(file.file.read())
    
    if file_ext == 'docx':
        text = extract_text_from_docx(file_path)
    elif file_ext == 'pdf':
        text = extract_text_from_pdf(file_path)
    else:
        text = ""
    
    os.remove(file_path)
    return text

def process_jd_image(file: UploadFile) -> str:
    file_ext = file.filename.split('.')[-1].lower()
    file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}.{file_ext}")
    
    with open(file_path, "wb") as f:
        f.write(file.file.read())
    
    text = extract_text_from_image(file_path)
    os.remove(file_path)
    return text

def build_jd_content(jd_text: str, jd_images: list) -> str:
    parts = []
    if jd_text.strip():
        parts.append(jd_text.strip())
    for img in (jd_images or []):
        if img.filename:
            content = process_jd_image(img)
            if content.strip():
                parts.append(content)
    return "\n\n".join(parts)

@app.post("/api/start")
async def start(
    jd_text: str = Form(""),
    jd_images: list[UploadFile] = File(None),
    resume_file: UploadFile = File(None),
    resume_text: str = Form("")
):
    jd_content = build_jd_content(jd_text, jd_images or [])
    if not jd_content.strip():
        raise HTTPException(400, "请填写JD文字描述或粘贴截图")
    if len(jd_content) > config.MAX_JD_LENGTH:
        jd_content = jd_content[:config.MAX_JD_LENGTH]
    
    resume_content = ""
    if resume_file:
        resume_content = process_resume_file(resume_file)
        if not resume_content.strip():
            raise HTTPException(400, "无法从简历文件中提取文字，请检查文件格式")
    elif resume_text.strip():
        resume_content = resume_text.strip()
    else:
        raise HTTPException(400, "请上传简历文件或使用AI生成简历")
    
    return analyze(new_id(), jd_content, resume_content)

@app.post("/api/generate-resume")
async def generate_resume(
    jd_text: str = Form(""),
    jd_images: list[UploadFile] = File(None),
    name: str = Form(""),
    skills: str = Form(""),
    experience: str = Form(""),
    position: str = Form(""),
    education: str = Form(""),
    notes: str = Form("")
):
    jd_content = build_jd_content(jd_text, jd_images or [])
    if not jd_content.strip():
        raise HTTPException(400, "请填写JD文字描述或粘贴截图")
    if len(jd_content) > config.MAX_JD_LENGTH:
        jd_content = jd_content[:config.MAX_JD_LENGTH]
    
    profile = {
        "name": name.strip(),
        "skills": skills.strip(),
        "experience": experience.strip(),
        "position": position.strip(),
        "education": education.strip(),
        "notes": notes.strip()
    }
    return generate_resume_and_tech(jd_content, profile)

@app.post("/api/download-resume")
async def download_resume(resume_text: str = Form(...)):
    from fpdf import FPDF
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("SimSun", "", "C:/Windows/Fonts/simsun.ttc", uni=True)
    pdf.set_font("SimSun", "", 10)
    pdf.set_auto_page_break(False)
    
    y = 15
    for line in resume_text.split("\n"):
        line = line.strip()
        if not line:
            y += 4
            continue
        if line.startswith("【") and "】" in line:
            pdf.set_font("SimSun", "", 12)
            pdf.set_xy(15, y)
            pdf.cell(0, 7, line, new_x="LMARGIN", new_y="NEXT")
            y = pdf.get_y() + 2
            pdf.set_font("SimSun", "", 10)
        else:
            pdf.set_xy(15, y)
            pdf.multi_cell(180, 5, line)
            y = pdf.get_y() + 1
        
        if y > 280:
            break
    
    buf = BytesIO()
    pdf.output(buf)
    buf.seek(0)
    
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=resume.pdf"}
    )

@app.get("/api/question")
async def question(session_id: str = Query(...), question_id: int = Query(None)):
    qs = get_questions(session_id)
    if not qs: raise HTTPException(404, "Session 不存在")
    qid = question_id or next((q["id"] for q in qs if str(q["id"]) not in get_answers(session_id)), None)
    if qid is None: return {"done": True}
    q = next((x for x in qs if x["id"]==qid), None)
    if not q: raise HTTPException(404)
    return {"question_id": q["id"], "category": q.get("category",""), "question": q["question"],
            "current": sum(1 for _ in get_answers(session_id).values())+1, "total": len(qs)}

@app.post("/api/answer")
async def answer(session_id: str = Form(...), question_id: int = Form(...), answer: str = Form(...)):
    if not answer.strip(): raise HTTPException(400, "回答不能为空")
    return score_answer(session_id, question_id, answer)

@app.get("/api/report")
async def report(session_id: str = Query(...)):
    return get_report(session_id)

FRONTEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend"))
if os.path.isdir(FRONTEND): app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")

@app.middleware("http")
async def add_no_cache_header(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8008"))
    uvicorn.run("main:app", host="0.0.0.0", port=port)