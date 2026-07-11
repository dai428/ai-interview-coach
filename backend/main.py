"""FastAPI — AI Interview Coach"""
import os, uuid
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import config
from interview_engine import new_id, analyze, score_answer, get_questions, get_answers, get_report

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
        from PIL import Image
        import pytesseract
        img = Image.open(file_path)
        return pytesseract.image_to_string(img, lang='chi_sim')
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

@app.post("/api/start")
async def start(
    jd_type: str = Form(...),
    jd_text: str = Form(""),
    jd_image: UploadFile = File(None),
    resume_file: UploadFile = File(None)
):
    # 处理JD
    jd_content = ""
    if jd_type == "text":
        if not jd_text.strip():
            raise HTTPException(400, "JD文字描述不能为空")
        jd_content = jd_text.strip()
    elif jd_type == "image":
        if not jd_image:
            raise HTTPException(400, "请上传JD截图")
        jd_content = process_jd_image(jd_image)
        if not jd_content.strip():
            raise HTTPException(400, "无法从截图中提取文字，请尝试文字输入")
    else:
        raise HTTPException(400, "无效的JD类型")
    
    # 处理简历
    if not resume_file:
        raise HTTPException(400, "请上传简历文件")
    
    resume_content = process_resume_file(resume_file)
    if not resume_content.strip():
        raise HTTPException(400, "无法从简历文件中提取文字，请检查文件格式")
    
    return analyze(new_id(), jd_content, resume_content)

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

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8008"))
    uvicorn.run("main:app", host="0.0.0.0", port=port)