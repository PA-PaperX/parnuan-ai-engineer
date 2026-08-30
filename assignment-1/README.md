# Parnuan AI Engineer — Assignment 1

โปรเจกต์นี้เป็น Proof of Concept สำหรับแยกข้อความการใช้จ่ายให้เป็นรายการธุรกรรม โดยใช้โมเดลภาษาเป็นตัวช่วยอ่านภาษาธรรมชาติ และใช้โค้ด Python เป็นคนตรวจคำตอบก่อนนำไปใช้

ข้อมูลที่ระบบต้องการดึงมี 2 อย่าง:

- `amount` จำนวนเงิน
- `detail` รายละเอียดว่าใช้เงินกับอะไร

ตัวอย่าง:

```text
ข้าวมันไก่ 50 และน้ำ 10
```

ผลลัพธ์ที่ต้องการ:

```json
{
  "transactions": [
    {"amount": 50, "detail": "ข้าวมันไก่"},
    {"amount": 10, "detail": "น้ำ"}
  ]
}
```

## ขอบเขตของงาน

งานนี้ทำเฉพาะการดึง `amount` และ `detail` ออกจากข้อความ ยังไม่รวมการจัดหมวดหมู่ การบันทึกฐานข้อมูล หรือการสร้างวันเวลา เพราะต้องการโฟกัสที่ความถูกต้องของการดึงข้อมูลและความปลอดภัยของคำตอบจากโมเดล

## วิธีติดตั้งและตรวจระบบ

ต้องมี Python 3.11 ขึ้นไปและติดตั้ง [uv](https://docs.astral.sh/uv/)

```powershell
cd assignment-1
uv sync
uv run pytest -q
uv run ruff check .
uv run ty check
```

ตรวจ dataset:

```powershell
uv run python -m transaction_ner.dataset
```

## ทดลองแบบไม่ส่งข้อมูลออกไป

โหมด offline ใช้สำหรับดู flow และตรวจ contract โดยไม่เรียก OpenRouter:

```powershell
uv run python -m transaction_ner.cli --offline "ข้าวมันไก่ 50"
```

โหมดนี้คืนค่า:

```json
{"transactions": []}
```

การคืนรายการว่างเป็นพฤติกรรมที่ตั้งใจไว้ เพราะ offline mode ไม่ได้ใช้โมเดลและไม่ควรเดาข้อมูลการเงินขึ้นมาเอง

## ทดลองหน้าเว็บในเครื่อง

```powershell
uv run python -m transaction_ner.web --offline
```

จากนั้นเปิด `http://127.0.0.1:8765`

หน้าเว็บเป็น local demo สำหรับดูการทำงานของระบบในรูปแบบที่อ่านง่าย มีช่องกรอกข้อความ ปุ่มตัวอย่าง สถานะการทำงาน ชื่อโมเดล เวลา response และรายการผลลัพธ์

## วิธีทดลองโมเดลจริง

ต้องใช้ API key ผ่าน environment variable เท่านั้น ไม่เขียน key ลงในโค้ด:

```powershell
$env:OPENROUTER_API_KEY = "<temporary-key>"
$env:MODEL_NAME = "google/gemma-4-26b-a4b-it:free"
uv run python -m transaction_ner.cli "ข้าวมันไก่ 50"
```

หรือเปิดหน้าเว็บแบบ online:

```powershell
uv run python -m transaction_ner.web --model "google/gemma-4-26b-a4b-it:free"
```

คำว่า local ในที่นี้หมายถึงโปรแกรมและหน้าเว็บรันอยู่ในเครื่องเราเท่านั้น ถ้าเลือก online ข้อความจะถูกส่งไปประมวลผลที่ OpenRouter ดังนั้นไม่ควรใส่ข้อมูลการเงินจริงหรือข้อมูลส่วนตัวในการทดลอง

## สิ่งที่ผมวิเคราะห์จากโจทย์

ผมมองว่าโมเดลภาษาเหมาะกับการอ่านข้อความที่เขียนได้หลายแบบ แต่ไม่ควรมีสิทธิ์ส่งคำตอบไปใช้โดยตรง เพราะคำตอบอาจไม่ครบ รูปแบบผิด หรือมีข้อมูลที่ไม่มีอยู่ในข้อความต้นฉบับ

ดังนั้นระบบจึงแบ่งหน้าที่เป็น 2 ส่วน:

1. โมเดลช่วยเสนอรายการจากภาษาธรรมชาติ
2. Python ตรวจว่าคำตอบอยู่ในรูปแบบที่กำหนดและอ้างอิงจากข้อความต้นฉบับจริง

ถ้าตรวจไม่ผ่าน ระบบจะคืนรายการว่างพร้อมสถานะความผิดพลาด แทนการส่งต่อข้อมูลที่ดูเหมือนถูกแต่จริง ๆ อาจผิด

## Flow การทำงาน

```text
ผู้ใช้ส่งข้อความ
        ↓
CLI หรือ local demo UI
        ↓
ตรวจ input เบื้องต้น
        ↓
สร้าง prompt และกั้นข้อความผู้ใช้ไว้ใน <input>
        ↓
เรียกโมเดลผ่าน OpenRouter
        ↓
อ่าน JSON response
        ↓
ตรวจ schema ด้วย Pydantic
        ↓
ตรวจว่า amount/detail มีอยู่ในข้อความต้นฉบับ
        ↓
คืนผลลัพธ์ที่ผ่านการตรวจ
```

ถ้าเกิดข้อความว่าง input ยาวเกินไป JSON ผิด API ล่ม หรือ rate limit ระบบจะเข้าสู่ fallback:

```text
คืน {"transactions": []} พร้อม status ที่บอกสาเหตุ
```

## เหตุผลที่เลือก Python

งานนี้เน้นการทดลองโมเดล ตรวจข้อมูล และวัดผลซ้ำ ๆ ผมจึงเลือก Python เพราะแบ่ง core logic ออกมาทดสอบได้ง่าย และมีเครื่องมือที่เหมาะกับงานข้อมูล:

- `Pydantic` ตรวจรูปแบบข้อมูลจากโมเดล
- `pytest` ทดสอบพฤติกรรมโดยไม่ต้องยิง API ทุกครั้ง
- `uv` ติดตั้ง dependency ได้เร็วและทำซ้ำได้
- Python เหมาะกับการเขียน evaluation และคำนวณ metrics

## แต่ละไฟล์ทำหน้าที่อะไร

| ไฟล์ | หน้าที่ |
| --- | --- |
| `schema.py` | กำหนดหน้าตาผลลัพธ์ที่ยอมรับ |
| `prompts.py` | กำหนดคำสั่งและกติกาที่ส่งให้โมเดล |
| `client.py` | ติดต่อ OpenRouter, อ่าน usage และจัดการ retry |
| `parser.py` | คุม flow ตรวจ input, parse output และ fallback |
| `evaluation.py` | รัน dataset และคำนวณ metrics |
| `web.py` | แสดง local demo UI |
| `tests/` | ทดสอบ input, output, error และ retry |

การแยกไฟล์แบบนี้ทำให้แก้ prompt, เปลี่ยน provider หรือปรับกฎตรวจคำตอบได้โดยไม่ต้องรื้อทั้งโปรเจกต์

## การตรวจคำตอบจากโมเดล

คำตอบจะผ่านการตรวจหลายชั้น:

1. ต้องเป็น JSON ที่อ่านได้
2. ต้องมีโครงสร้างตาม schema
3. `amount` ต้องเป็นตัวเลขที่ถูกต้อง
4. `detail` ต้องไม่ว่าง
5. ห้ามมี field แปลกปลอม
6. `amount` และ `detail` ต้องมีหลักฐานอยู่ในข้อความ input

ชั้นสุดท้ายเรียกว่า grounding check จุดประสงค์คือป้องกันโมเดลสร้างรายการหรือจำนวนเงินที่ไม่มีอยู่ในข้อความ

## การจัดการ API ล้มเหลว

ถ้าเจอ HTTP 429 หรือ 503 ระบบจะลองใหม่โดยเว้นระยะเพิ่มขึ้นแบบ exponential backoff และอ่านค่า `Retry-After` ถ้ามี

เมื่อ retry ครบแล้วยังไม่สำเร็จ ระบบจะไม่ค้างและไม่ทำให้ผู้ใช้เห็นข้อมูลปลอม แต่คืนรายการว่างพร้อมสถานะ เช่น:

- `rate_limited` เรียกถี่เกินไป
- `invalid_model_output` JSON หรือ schema ไม่ถูกต้อง
- `ungrounded_model_output` คำตอบไม่มีหลักฐานใน input
- `input_empty` ไม่มีข้อความให้ประมวลผล

การแยกสถานะออกจากรายการว่างช่วยให้รู้ว่ารายการว่างเกิดจากอะไร

## Dataset และการวัดผล

ไฟล์ `dataset/examples.jsonl` มีข้อมูลสังเคราะห์ 80 ตัวอย่าง แบ่งเป็น:

| กลุ่ม | จำนวน | ใช้ทดสอบ |
| --- | ---: | --- |
| `happy` | 25 | ข้อความที่เขียนชัดเจน |
| `messy` | 25 | typo, slang, spacing และไทยผสมอังกฤษ |
| `non_transaction` | 15 | ข้อความที่ไม่ใช่ธุรกรรม |
| `adversarial` | 15 | prompt injection และ input ผิดปกติ |

รัน benchmark:

```powershell
uv run python -m transaction_ner.eval `
  --models "google/gemma-4-31b-it:free,google/gemma-4-26b-a4b-it:free" `
  --output eval/eval_report.json `
  --output-md eval/eval_report.md
```

รายงานที่บันทึกไว้:

- [`eval/eval_report.json`](./eval/eval_report.json) ข้อมูลผลลัพธ์แบบ JSON
- [`eval/eval_report.md`](./eval/eval_report.md) รายงานแบบอ่านง่าย

ตัวชี้วัดหลักคือ `Amount F1`, `Detail F1`, `Exact match`, `Count accuracy`, latency และ failure taxonomy การดูเฉพาะ F1 อย่างเดียวไม่พอ เพราะโมเดลฟรีอาจตอบไม่ได้เนื่องจาก rate limit

## ผล benchmark ที่มีอยู่

จากการทดสอบ 80 ตัวอย่างต่อโมเดล:

| โมเดล | Amount F1 | Detail F1 | Exact match | Count accuracy | p50 / p95 (ms) |
| --- | ---: | ---: | ---: | ---: | ---: |
| `google/gemma-4-26b-a4b-it:free` | **0.976** | **0.784** | **81.25%** | **96.25%** | 3,401.9 / 15,349.3 |
| `google/gemma-4-31b-it:free` | 0.197 | 0.169 | 40.00% | 41.25% | 15,165.6 / 17,029.6 |

จากผลรอบนี้ 26B เหมาะกว่าในฐานะ candidate สำหรับ free endpoint เพราะดึงจำนวนเงินและนับจำนวนรายการได้ดีกว่า ส่วน 31B มี rate limit สูงมาก จึงยังไม่ควรสรุปว่าเป็นโมเดลที่คุณภาพต่ำกว่า

ผล benchmark เป็นหลักฐานจาก dataset และช่วงเวลาหนึ่ง ไม่ใช่การรับประกันว่าโมเดลจะตอบเหมือนเดิมทุกข้อความ

## ข้อจำกัดที่ทราบ

- Dataset เป็นข้อมูลสังเคราะห์เพียง 80 ตัวอย่าง ยังเล็กเกินไปสำหรับสรุปคุณภาพ production
- Free endpoint มี rate limit และ availability เปลี่ยนแปลงได้
- Detail F1 ต่ำกว่า Amount F1 เพราะการเลือกขอบเขตรายละเอียดให้ตรง label ทำได้ยากกว่าอ่านตัวเลข
- ระบบยังไม่มี local model จึงไม่ใช่ offline inference ในความหมายของการรันโมเดลบนเครื่อง
- ยังไม่มี confidence score ต่อ field
- การใช้ `data_collection=deny` เป็น request policy ไม่ได้แปลว่าข้อความไม่ออกจากเครื่องเมื่อใช้ online mode

## ถ้ามีเวลาเพิ่มจะทำอะไรต่อ

1. เพิ่มข้อมูลทดสอบที่มาจากข้อความจริงแบบลบข้อมูลส่วนตัวแล้ว
2. เพิ่มตัวอย่างที่ครอบคลุมรูปแบบการเขียนภาษาไทยมากขึ้น
3. เพิ่ม confidence score และแสดงเหตุผลที่ระบบปฏิเสธคำตอบ
4. เพิ่ม local deterministic fast path สำหรับรูปแบบข้อความที่อ่านได้ชัด
5. ทดลอง local model เมื่อมีเครื่องมือและทรัพยากรเหมาะสม

## การใช้เครื่องมือช่วย

ผมใช้เครื่องมือช่วยค้นแนวทาง ตรวจ syntax และช่วยคิดกรณีทดสอบบางส่วน แต่เป็นคนเลือกขอบเขต ออกแบบ contract, validation, fallback และอ่านผล benchmark ด้วยตัวเอง

## เวลาที่ใช้

ใช้เวลาประมาณ 4.5 ชั่วโมง แบ่งคร่าว ๆ เป็น:

- วาง contract และ project setup: 30 นาที
- ออกแบบ dataset และ validation: 45 นาที
- เชื่อม OpenRouter และเขียน prompt: 1 ชั่วโมง
- ทำ evaluation และ backoff: 1 ชั่วโมง
- ทำ tests และ documentation: 45 นาที
- ทำ benchmark, report และตรวจ security: 30 นาที

## Git workflow

ผมแยกงานเป็น branch ตามช่วงการพัฒนา เพื่อให้เห็นว่าฟีเจอร์ไหนมาก่อนหลัง:

1. `assignment-1/contract-scaffold` — วาง schema, CLI และ contract tests
2. `assignment-1/dataset-validation` — เพิ่ม dataset และ validation
3. `assignment-1/openrouter-provider` — เพิ่ม client, prompt และ fallback
4. `assignment-1/evaluation` — เพิ่ม metrics, latency และ failure taxonomy
5. `assignment-1/local-demo-ui` — เพิ่มหน้าเว็บสำหรับทดลอง

แต่ละช่วงมี commit แยกและสามารถย้อนดูได้ โดย `main` เป็นเวอร์ชันรวมสำหรับส่งงาน
