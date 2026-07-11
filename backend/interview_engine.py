"""面试引擎"""
import json, re, uuid
from openai import OpenAI
from fastapi import HTTPException
import config

client = OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url=config.DEEPSEEK_API_BASE)
sessions = {}

def _llm_json(sp, up):
    try:
        r = client.chat.completions.create(model=config.LLM_MODEL, messages=[{"role":"system","content":sp},{"role":"user","content":up}], temperature=0.4, response_format={"type":"json_object"})
        t = re.sub(r'^```(?:json)?\s*|\s*```$', '', r.choices[0].message.content.strip())
        return json.loads(t)
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"Raw content: {r.choices[0].message.content[:500]}")
        raise HTTPException(500, "AI 返回格式异常，请重试")
    except Exception as e:
        print(f"LLM error: {e}")
        raise HTTPException(500, f"AI 服务异常: {str(e)}")

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

GEN_RESUME_PROMPT = """你是一位资深的职业规划师和简历专家，说话亲切、专业、接地气。根据招聘JD和候选人提供的信息，请你帮候选人做三件事：

1. 生成一份与JD匹配的真实可信的简历。如果候选人提供了个人信息，基于这些信息来写；如果某部分信息为空，你根据JD要求自动生成最优的、真实可信的内容。
2. 分析该岗位需要掌握的核心技术栈，并标注每个技术的掌握程度建议
3. 为候选人规划一条学习路径，推荐具体的学习资源

===== 简历书写规范（严格遵循）=====

【整体原则】
- 一页A4纸，简洁明了，不要花里胡哨
- 简历上写的每一项都会成为面试考点，拿不准的绝对不要写，不熟的技能不要写
- 突出3-5个核心技能点，不要面面俱到。面试官重点考察你写出来的技能
- 技术名词大小写严格规范：如 MySQL 不是 mysql，Java 不是 java，Redis 不是 redis

【简历结构】
1. 个人信息：姓名、电话、邮箱、求职意向（一行即可，简洁）
2. 个人优势：2-3句话，突出核心竞争力和经验亮点
3. 技能清单：分门别类，每类只列真正掌握的
   - 编程语言：Java、Python 等
   - 框架：Spring Boot、MyBatis 等
   - 数据库与中间件：MySQL、Redis、Kafka 等
   - 工具与其他：Git、Docker、Linux 等
4. 工作/项目经历：每段经历包含：
   - 项目名称/公司 · 时间
   - 项目描述：一句话说清楚项目做什么
   - 技术栈：用了什么技术
   - 个人职责：做了什么、解决了什么问题、有什么成果（尽量量化）
   - 用 STAR 法则（情境-任务-行动-结果）描述，突出个人贡献
5. 教育背景：学校、学历、专业、时间（简洁）

【排版规范】
- 中英文之间加空格，如："使用 Java 开发"
- 中文和数字之间加空格，如："3 年经验"
- 不要使用表格、复杂配色、图片
- 简历整体风格简洁专业，像高质量 Markdown 渲染效果

===== 输出格式 =====
输出JSON格式：
{
    "resume": "完整的简历内容，严格按上述规范书写，每部分用【】中文标题标注，不要用markdown表格，语言精炼",
    "tech_stack": [
        {"name": "技术名称", "level": "掌握程度（精通/熟练/了解）", "why": "为什么这个岗位需要这个技术"}
    ],
    "learning_path": [
        {"topic": "学习主题", "resources": "推荐的具体学习资源（书名/网站/课程名）", "why": "为什么要学这个", "time_estimate": "预计学习时间"}
    ],
    "interview_tips": "针对该岗位的3-5条面试小贴士，语气要像朋友在分享经验",
    "match_analysis": "候选人匹配度分析，指出哪些JD要求可以满足，哪些还需要补强"
}

===== 注意事项 =====
- 如果候选人提供了姓名，使用真实姓名；否则生成一个合理的名字
- 简历必须精炼，控制在A4纸一页以内
- 不熟的技能宁可少写，不要多写。面试官会追着你写的每一项技能提问
- 项目经历要有具体细节，不要泛泛而谈"参与了XX系统开发"
- 学习路径要具体可执行，不要泛泛而谈
- 整体语气要温暖鼓励，像是在帮朋友准备面试"""

def generate_resume_and_tech(jd_content, profile=None):
    profile = profile or {}
    profile_text = ""
    if profile.get("name"): profile_text += f"姓名：{profile['name']}\n"
    if profile.get("skills"): profile_text += f"已有技能：{profile['skills']}\n"
    if profile.get("experience"): profile_text += f"工作经验：{profile['experience']}\n"
    if profile.get("position"): profile_text += f"目标岗位：{profile['position']}\n"
    if profile.get("education"): profile_text += f"教育背景：{profile['education']}\n"
    if profile.get("notes"): profile_text += f"补充说明：{profile['notes']}\n"

    user_msg = f"## 招聘JD\n{jd_content}\n\n"
    if profile_text:
        user_msg += f"## 候选人提供的信息\n{profile_text}\n\n请基于候选人提供的信息，对缺失的部分自动补全，生成一份完整的简历。"
    else:
        user_msg += "候选人没有提供任何个人信息，请根据JD自动生成一份最优的、真实可信的简历。"

    result = _llm_json(GEN_RESUME_PROMPT, user_msg)
    return result

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