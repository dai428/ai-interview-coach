"""面试引擎"""
import json, re, uuid
from openai import OpenAI
import config

client = OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url=config.DEEPSEEK_API_BASE)
sessions = {}

def _llm_json(sp, up):
    r = client.chat.completions.create(model=config.LLM_MODEL, messages=[{"role":"system","content":sp},{"role":"user","content":up}], temperature=0.4, response_format={"type":"json_object"})
    t = re.sub(r'^```(?:json)?\s*|\s*```$', '', r.choices[0].message.content.strip())
    return json.loads(t)

Q_PROMPT = """你是一位经验丰富的面试官，说话亲切自然，喜欢用"咱们"、"比如说"、"你觉得呢"这类口语化表达。你的任务是：
1. 先热情地打招呼，简单介绍自己，让候选人放松下来
2. 根据JD和简历，自然地进行一场模拟面试，大约6-8个问题，涵盖技术功底、项目经验、场景应变、行为特质
3. 问题要像聊天一样自然抛出，不要机械罗列，每个问题前面可以有一两句自然的过渡
4. 每个问题要能考察候选人的真实水平，不要太简单也不要太刁钻

输出JSON格式：
{"greeting": "面试官的开场白，包含打招呼和简单介绍，语气亲切自然，2-3句话",
 "questions": [{"id":1,"category":"技术功底","question":"像聊天一样自然的问题","criteria":"考察要点","model_answer":"作为面试官会怎么评价好的回答","target_skill":"考察的技能点"}]}

注意：question必须是口语化的问题，要像真人面试官会问的那样，不要太书面化。"""

S_PROMPT = """你是那位面试官，刚刚听完候选人的回答。请像真人面试官一样给出反馈：
1. 先简要点评一下回答（自然的口吻，不要像评分机器）
2. 指出得分（1-10分），说明为什么
3. 给一句具体的改进建议
4. 分享你自己对这个问题的看法（作为面试官的经验之谈）

输出JSON：
{"score":7,"feedback":"像真人面试官一样的自然点评，2-3句话，有鼓励也有指出不足","strengths":"回答的亮点","weaknesses":"可以改进的地方","suggestion":"具体的改进建议，语气要像朋友给的忠告","model_answer":"如果是一个优秀的回答，可能是什么样的"}

feedback要自然，不要用"优点：xxx 不足：xxx"这种格式，而是像聊天一样说"嗯，你刚才提到的xxx很不错，不过我觉得xxx方面还可以再深入一些"。"""

R_PROMPT = """你刚刚完成了一场模拟面试，现在要给候选人一个总结性的反馈。请像一位真诚的导师一样，给出全面的面试总结。语气要温暖、鼓励，但同时也要实事求是地指出需要提升的地方。

输出JSON：
{"overall_assessment":"一段自然的面试总结，2-3句话，包括整体印象和表现评价",
 "strength_areas":["优势1","优势2","优势3"],
 "weakness_areas":["待提升1","待提升2"],
 "preparation_suggestions":["备考建议1","备考建议2","备考建议3"],
 "recommended_focus":"最需要重点准备的方向，一句话说清楚"}

整体语气要像一个关心你的前辈在给你复盘，不要说官话套话。"""

def new_id():
    return uuid.uuid4().hex[:12]

def analyze(sid, jd, resume):
    sessions[sid] = {"jd": jd, "resume": resume, "questions": [], "answers": {}}
    result = _llm_json(Q_PROMPT, f"## JD\n{jd}\n\n## 简历\n{resume}")
    qs = result.get("questions", [])
    for i, q in enumerate(qs): q["id"] = int(q.get("id", i+1))
    sessions[sid]["questions"] = qs
    sessions[sid]["greeting"] = result.get("greeting", "你好！欢迎参加今天的模拟面试，我看了你的简历，咱们开始吧。")
    return {"session_id": sid, "total": len(qs), "greeting": sessions[sid]["greeting"], "questions": [{"id":q["id"],"category":q.get("category",""),"question":q["question"]} for q in qs]}

def score_answer(sid, qid, answer):
    s = sessions.get(sid, {}); q = next((x for x in s.get("questions",[]) if x["id"]==qid), None)
    if not q: raise ValueError("题目不存在")
    r = _llm_json(S_PROMPT, f"## 题目\n{q['question']}\n\n## 评分标准\n{q.get('criteria','')}\n\n## 模型答案\n{q.get('model_answer','')}\n\n## 回答\n{answer}")
    s["answers"][str(qid)] = {"question":q["question"],"category":q.get("category",""),"user_answer":answer,"score":r.get("score",5),"feedback":r.get("feedback",""),"strengths":r.get("strengths",""),"weaknesses":r.get("weaknesses",""),"suggestion":r.get("suggestion",""),"model_answer":r.get("model_answer",q.get("model_answer",""))}
    return r

def get_questions(sid):
    s = sessions.get(sid, {})
    return s.get("questions", [])

def get_answers(sid):
    s = sessions.get(sid, {})
    return s.get("answers", {})

def get_report(sid):
    s = sessions.get(sid, {}); answers = s.get("answers", {})
    if not answers: raise ValueError("还没有回答记录")
    total = sum(a.get("score",0) for a in answers.values()); mx = len(answers)*10
    detail = "\n".join(f"Q{k} [{a.get('category','')}] {a.get('score',0)}/10  优点：{a.get('strengths','')}  不足：{a.get('weaknesses','')}" for k,a in answers.items())
    r = _llm_json(R_PROMPT, f"共{len(answers)}题，总分{total}/{mx}（{total/mx*100:.0f}%）。\n\n{detail}")
    r["total_answered"]=len(answers); r["total_questions"]=len(s.get("questions",[])); r["raw_score"]=total; r["max_score"]=mx; r["percentage"]=round(total/mx*100,1) if mx>0 else 0
    r["details"] = []
    for q in s.get("questions",[]):
        a = answers.get(str(q["id"]))
        if a: r["details"].append({"id":q["id"],"category":q.get("category",""),"question":q["question"],"user_answer":a["user_answer"],"score":a["score"],"strengths":a.get("strengths",""),"weaknesses":a.get("weaknesses",""),"suggestion":a.get("suggestion",""),"model_answer":a.get("model_answer","")})
    s["completed"] = True
    return r