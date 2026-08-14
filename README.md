# Parnuan AI Engineer — Assignment 1

โปรเจกต์นี้เป็นคำตอบสำหรับตำแหน่ง **AI Engineer** ของ Parnuan

ระบบรับข้อความการใช้จ่ายภาษาไทยหรือไทยผสมอังกฤษ แล้วแยกออกมาเป็นรายการธุรกรรมแบบมีโครงสร้าง โดยเน้นการออกแบบ dataset, การประเมินโมเดล, ความปลอดภัยของ output และการรับมือ API failure

อ่านรายละเอียดทั้งหมดได้ที่ [`assignment-1/README.md`](./assignment-1/README.md)

## สิ่งที่อยู่ในโปรเจกต์

- `Text → Transaction NER` แยก `amount` และ `detail`
- Dataset สังเคราะห์ 80 ตัวอย่าง พร้อม bucket และ label validation
- Evaluation เปรียบเทียบโมเดล OpenRouter 2 รุ่น
- Pydantic schema, grounding check และ graceful degradation
- Local demo UI สำหรับทดลองโดยไม่ส่งข้อมูลออกจากเครื่อง

## วิธีเริ่มต้นอย่างปลอดภัย

```powershell
cd assignment-1
uv sync
uv run pytest -q
uv run python -m transaction_ner.web --offline
```

จากนั้นเปิด `http://127.0.0.1:8765`

โหมดนี้ไม่เรียก OpenRouter และคืนรายการว่างโดยตั้งใจ หากต้องการทดสอบโมเดลจริง ให้ดูคำสั่งและข้อควรระวังใน [assignment-1/README.md](./assignment-1/README.md)

## ประวัติ Git และลำดับการพัฒนา

- `assignment-1/contract-scaffold`
- `assignment-1/dataset-validation`
- `assignment-1/openrouter-provider`
- `assignment-1/evaluation`
- `assignment-1/local-demo-ui`

แต่ละ branch แสดงพัฒนาการคนละช่วง และ `main` เป็นเวอร์ชันรวมสำหรับส่งงาน
