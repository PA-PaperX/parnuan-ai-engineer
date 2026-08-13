# Parnuan Engineer Dev

โปรเจกต์นี้เป็นคำตอบ Assignment 1 ระบบแยกรายการใช้จ่ายจากข้อความภาษาไทย

เริ่มอ่านรายละเอียดทั้งหมดที่ [`assignment-1/README.md`](./assignment-1/README.md)

## จุดเริ่มต้นที่แนะนำ

```powershell
cd assignment-1
uv sync
uv run pytest -q
uv run python -m transaction_ner.web --offline
```

จากนั้นเปิด `http://127.0.0.1:8765`

## ประวัติ Git

- `assignment-1/contract-scaffold`
- `assignment-1/dataset-validation`
- `assignment-1/openrouter-provider`
- `assignment-1/evaluation`
- `assignment-1/local-demo-ui`

แต่ละ branch แสดงพัฒนาการคนละช่วง และ `main` เป็นเวอร์ชันรวมสำหรับส่งงาน
