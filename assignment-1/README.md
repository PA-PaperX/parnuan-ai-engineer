# ระบบแยกรายการใช้จ่ายจากข้อความภาษาไทย

โปรเจกต์นี้เป็นคำตอบสำหรับ Assignment 1 ของ Parnuan โดยรับข้อความการใช้เงินที่ผู้ใช้พิมพ์ตามธรรมชาติ แล้วแยกออกมาเป็นรายการธุรกรรมที่มีข้อมูล 2 อย่าง:

- `amount` จำนวนเงิน
- `detail` รายละเอียดว่าใช้เงินกับอะไร

ตัวอย่าง:

ข้อความเข้า:

```text
ข้าวมันไก่ 50 และน้ำ 10
```

ผลลัพธ์:

```json
{
  "transactions": [
    {"amount": 50, "detail": "ข้าวมันไก่"},
    {"amount": 10, "detail": "น้ำ"}
  ]
}
```

โปรเจกต์นี้ทำเฉพาะชั้น `NER` หรือการดึงข้อมูลสำคัญออกจากข้อความ ยังไม่ทำการจัดหมวดหมู่ ไม่บันทึกฐานข้อมูล และไม่สร้าง timestamp เพราะอยู่นอกขอบเขตของโจทย์

## สรุปแนวคิดในหนึ่งย่อหน้า

ผมเริ่มจากกำหนดหน้าตาของข้อมูลที่ถูกต้องก่อนเรียก AI เพื่อให้ระบบรู้เสมอว่าผลลัพธ์ต้องมีรูปแบบอย่างไร จากนั้นจึงแยกส่วนติดต่อ OpenRouter ออกจากส่วนตรวจข้อมูล เมื่อโมเดลตอบผิด รูปแบบ JSON ไม่ถูกต้อง หรือ API ใช้งานไม่ได้ ระบบจะไม่ปล่อยข้อมูลที่ไม่น่าเชื่อถือออกไป แต่จะคืนค่า `transactions: []` และระบุสถานะความผิดพลาดแทน

## ทำไมเลือก Python

โจทย์นี้เน้นการประเมินคุณภาพของโมเดลมากกว่าการทำหน้าตาแอป ผมจึงเลือก Python เพราะเหมาะกับงาน NLP และการทำ evaluation:

- ใช้ `Pydantic` ตรวจรูปแบบข้อมูลจากโมเดล
- ใช้ `pytest` เขียน automated tests
- ใช้ `uv` จัดการ dependency และทำให้ติดตั้งซ้ำได้ง่าย
- เขียน CLI และ evaluation harness ได้ตรงไปตรงมา
- ทำ fake provider เพื่อทดสอบโดยไม่ต้องยิง API จริงได้

นอกจาก Python core แล้ว มี local demo UI ขนาดเล็กสำหรับคนที่ไม่ถนัด command line โดย UI เรียก parser ตัวเดียวกับ CLI และ evaluation ไม่ได้มี business logic แยกอีกชุดหนึ่ง

## Flow การทำงาน

```text
ผู้ใช้พิมพ์ข้อความ
        ↓
CLI หรือ local demo UI
        ↓
Parser ตรวจ input
        ↓
สร้าง prompt และใส่ข้อความไว้ใน <input> boundary
        ↓
OpenRouter ส่งข้อความให้โมเดลที่เลือก
        ↓
อ่าน JSON response
        ↓
Pydantic ตรวจ schema
        ↓
คืน transactions ที่ผ่านการตรวจ
```

กรณีที่ระบบไม่มั่นใจหรือทำงานต่อไม่ได้:

```text
ข้อความว่าง / ยาวเกิน / API ล่ม / rate limit / JSON ผิด
        ↓
คืน {"transactions": []}
```

การคืนรายการว่างเป็นการออกแบบ `graceful degradation` ซึ่งเหมาะกับข้อมูลการเงินมากกว่าการเดาตัวเลขหรือสร้างธุรกรรมปลอม

## โครงสร้างไฟล์

```text
assignment-1/
├── dataset/
│   └── examples.jsonl          # ตัวอย่าง input และ label ที่ตรวจไว้
├── eval/
│   ├── eval_report.json        # ผลประเมินแบบ machine-readable
│   └── eval_report.md          # ผลประเมินแบบอ่านง่าย
├── src/transaction_ner/
│   ├── schema.py                # กำหนด output contract
│   ├── prompts.py               # prompt และกติกาการ extract
│   ├── client.py                # ติดต่อ OpenRouter
│   ├── parser.py                # คุม flow, parse, validate, fallback
│   ├── dataset.py               # โหลดและตรวจ dataset
│   ├── evaluation.py            # metrics และ failure taxonomy
│   ├── cli.py                   # ใช้งานผ่าน terminal
│   └── web.py                   # local receipt-like demo UI
├── tests/                       # automated tests
├── pyproject.toml
└── uv.lock
```

### หน้าที่ของไฟล์สำคัญ

`schema.py` เป็นกติกากลางของระบบ โดยกำหนดว่า transaction ต้องมี `amount` และ `detail` เท่านั้น ห้ามมี field แปลกปลอม และ `detail` ต้องไม่เป็นข้อความว่าง

`client.py` มีหน้าที่คุยกับ OpenRouter อย่างเดียว เช่น ส่ง request, อ่าน usage, จับ HTTP error และจัดการ retry เมื่อเจอ HTTP 429

`parser.py` มีหน้าที่คุมพฤติกรรมของแอป ไม่ว่าข้อมูลจะมาจาก OpenRouter หรือ fake provider ก็ต้องผ่านขั้นตอน parse และ validate เดียวกัน

`web.py` เป็นเพียงชั้นแสดงผลสำหรับผู้ใช้ ไม่ได้คัดลอก logic จาก parser ไปไว้ในหน้าเว็บ จึงยังทดสอบ core ได้จาก CLI และ pytest

## วิธีติดตั้งและตรวจระบบ

ต้องมี Python 3.11 ขึ้นไปและติดตั้ง [uv](https://docs.astral.sh/uv/)

```powershell
uv sync
uv run pytest -q
uv run ruff check .
uv run ty check
```

ผลตรวจล่าสุดของ repository นี้:

- `16 tests passed`
- Ruff ผ่าน
- ty ผ่าน
- dataset ผ่านการตรวจ 80 ตัวอย่าง

## ทดลองแบบไม่ส่งข้อมูลออกไป

คำสั่งนี้ไม่เรียก OpenRouter และใช้ตรวจ contract หรือทดลอง flow พื้นฐาน:

```powershell
uv run python -m transaction_ner.cli --offline "ข้าวมันไก่ 50"
```

ผลลัพธ์แบบ offline จะเป็นรายการว่างโดยตั้งใจ เพราะ offline mode ไม่ได้ใช้โมเดล:

```json
{"transactions": []}
```

## ใช้งานผ่าน OpenRouter

ต้องตั้ง API key ผ่าน environment variable เท่านั้น ห้ามใส่ key ลง source code, README หรือ commit:

```powershell
$env:OPENROUTER_API_KEY = "<new-key>"
$env:MODEL_NAME = "google/gemma-4-26b-a4b-it:free"
uv run python -m transaction_ner.cli "ข้าวมันไก่ 50"
```

ระบบตั้งค่าเหล่านี้เป็นค่าเริ่มต้น:

- `temperature = 0` เพื่อให้ผลมีความแปรปรวนน้อยลง
- จำกัด input ไว้ไม่เกิน 4,000 ตัวอักษร
- ขอให้โมเดลตอบ JSON
- ส่ง `provider.data_collection = deny` เป็นค่าเริ่มต้น
- retry HTTP 429 ด้วย exponential backoff 2, 4 และ 8 วินาที

คำว่า local ในที่นี้หมายถึงโปรแกรมและหน้า UI เปิดอยู่บนเครื่องเรา ไม่ได้หมายความว่าโมเดลทำงานอยู่บนเครื่อง ข้อความปกติจะถูกส่งไป OpenRouter ดังนั้นไม่ควรใส่ข้อมูลการเงินจริงหรือข้อมูลส่วนตัวของผู้ใช้

## Local demo UI

สำหรับคนที่ไม่ถนัด terminal ให้เปิดหน้า demo:

```powershell
uv run python -m transaction_ner.web
```

แล้วเปิด `http://127.0.0.1:8765`

หน้า UI ใช้แนวคิดใบเสร็จเพื่อให้ผู้ใช้เห็นลำดับข้อมูลได้ง่าย มี:

- ช่องกรอกข้อความภาษาไทยหรือไทยผสมอังกฤษ
- ปุ่มตัวอย่างรายการเดียวและหลายรายการ
- ตัวอย่างข้อความที่ไม่ใช่ธุรกรรมและข้อความแปลก
- สถานะการทำงาน
- ชื่อโมเดลและ latency
- ผลลัพธ์เป็นรายการที่อ่านง่าย

ถ้าต้องการดูหน้าตาโดยไม่ส่ง request ไปที่ OpenRouter:

```powershell
uv run python -m transaction_ner.web --offline
```

UI ไม่เก็บข้อความ และ server ไม่พิมพ์ request body ลง terminal

## Dataset

ไฟล์ `dataset/examples.jsonl` มีข้อมูลสังเคราะห์ 80 ตัวอย่าง และตรวจ label ด้วย Pydantic ก่อนใช้งาน แบ่งเป็น 4 กลุ่ม:

| กลุ่ม | จำนวน | สิ่งที่ทดสอบ |
|---|---:|---|
| `happy` | 25 | ข้อความชัดเจน ทั้งรายการเดียวและหลายรายการ |
| `messy` | 25 | typo, slang, spacing แปลก และไทยผสมอังกฤษ |
| `non_transaction` | 15 | คำทักทาย คำถาม และข้อความที่ไม่ใช่การใช้เงิน |
| `adversarial` | 15 | prompt injection, input ผิดปกติ, field ไม่ครบ และข้อความยาว |

Dataset นี้ใช้ข้อมูลสังเคราะห์ ไม่มีข้อมูลการเงินจริง จึงปลอดภัยสำหรับการพัฒนา แต่ยังไม่ควรอ้างว่าเป็นตัวแทนของผู้ใช้จริงทั้งหมด สิ่งที่ควรทำต่อคือขอข้อมูลที่ anonymize แล้วและให้คนตรวจ label เพิ่ม

ตรวจ dataset ด้วย:

```powershell
uv run python -m transaction_ner.dataset
```

## วิธีวัดผล

Evaluation harness รัน input ชุดเดียวกันผ่านแต่ละโมเดล แล้วเปรียบเทียบกับ label ที่เตรียมไว้ รายงานมีตัวชี้วัดดังนี้:

- `Precision` โมเดลตอบสิ่งที่ถูกต้องมากน้อยแค่ไหนเมื่อเทียบกับสิ่งที่ตอบทั้งหมด
- `Recall` โมเดลดึงสิ่งที่ควรได้ออกมาได้ครบแค่ไหน
- `F1` ค่ากลางระหว่าง precision และ recall
- `Exact match` array ของธุรกรรมทั้งชุดตรงกันหรือไม่
- `Count accuracy` จำนวนรายการที่ดึงออกมาตรงกับ label หรือไม่
- `p50/p95 latency` เวลาตอบในค่ากลางและช่วงท้ายของการกระจาย
- `$ / 1k messages` ค่าใช้จ่ายประมาณการต่อ 1,000 ข้อความเมื่อ provider ส่ง usage cost กลับมา

รัน benchmark:

```powershell
uv run python -m transaction_ner.eval `
  --models "google/gemma-4-31b-it:free,google/gemma-4-26b-a4b-it:free" `
  --output eval/eval_report.json `
  --output-md eval/eval_report.md
```

ใช้ `--limit 5` สำหรับ smoke test ก่อนรันเต็ม

Failure taxonomy แยกกรณีที่ผลผิดออกจากกัน เช่น:

- `missed_transaction` ไม่พบธุรกรรมที่ควรมี
- `wrong_amount` จำนวนเงินผิด
- `wrong_or_truncated_detail` รายละเอียดผิดหรือตัดไม่ครบ
- `merged_transactions` รวมหลายธุรกรรมเป็นรายการเดียว
- `hallucinated_transaction` สร้างธุรกรรมที่ไม่มีใน input
- `rate_limited` provider ไม่ให้เรียกเพราะเกิน rate limit

## ผล benchmark ที่บันทึกไว้

ผลนี้มาจาก 80 ตัวอย่างต่อโมเดล รวม 160 evaluation inputs โดยใช้ข้อมูลสังเคราะห์ รายงานฉบับเต็มอยู่ที่:

- [`eval/eval_report.json`](./eval/eval_report.json)
- [`eval/eval_report.md`](./eval/eval_report.md)

| โมเดล | Amount F1 | Detail F1 | Exact match | Count accuracy | p50 / p95 (ms) | $/1k |
|---|---:|---:|---:|---:|---:|---:|
| `google/gemma-4-26b-a4b-it:free` | **0.976** | **0.784** | **81.25%** | **96.25%** | 3,401.9 / 15,349.3 | $0.00 |
| `google/gemma-4-31b-it:free` | 0.197 | 0.169 | 40.00% | 41.25% | 15,165.6 / 17,029.6 | $0.00 |

### การอ่านผลอย่างระมัดระวัง

จาก run นี้ `google/gemma-4-26b-a4b-it:free` เป็น candidate ที่เหมาะกว่า เพราะดึง amount ได้ดี นับจำนวนธุรกรรมได้ถูกต้องสูง และมี successful responses มากกว่า

ผลแยกตาม bucket ของ 26B:

- `non_transaction`: exact match 100%
- `adversarial`: 86.7%
- `messy`: 76.0%
- `happy`: 72.0%

ความผิดหลักคือ `wrong_or_truncated_detail` 12 ครั้ง และ `missed_transaction` 1 ครั้ง ส่วน rate limit พบ 7 ครั้งจาก 80 requests

สำหรับ 31B พบ rate limit สูงมาก โดย status เป็น `rate_limited: 68`, `ok: 9` และ `input_empty: 3` จึงยังสรุปคุณภาพพื้นฐานของโมเดล 31B ไม่ได้อย่างยุติธรรม คะแนนต่ำของ run นี้สะท้อน availability ของ free provider เป็นหลัก ไม่ใช่หลักฐานว่าโมเดลภาษาด้อยกว่า 26B

ดังนั้นคำแนะนำที่ถูกต้องคือ:

> สำหรับ free shared endpoint จาก benchmark นี้ ให้ใช้ `google/gemma-4-26b-a4b-it:free` เป็น candidate หลัก แต่ต้องมี monitoring, retry, timeout และแผนเปลี่ยน provider ก่อนใช้งาน production จริง ส่วน 31B ต้องทดสอบใหม่ในช่วงที่ rate limit น้อยลงก่อนตัดสินคุณภาพ

## ข้อจำกัดของผลลัพธ์

- Dataset เป็นข้อมูลสังเคราะห์ 80 ตัวอย่าง ยังเล็กเกินไปสำหรับสรุป production quality
- Free endpoint มี rate limit และ availability เปลี่ยนแปลงได้
- `p95` ของ 26B ประมาณ 15.3 วินาที จึงอาจช้าเกินไปสำหรับประสบการณ์ใช้งานจริง
- Detail F1 ต่ำกว่า Amount F1 เพราะการเลือกข้อความรายละเอียดให้ตรง label ทำได้ยากกว่าแค่ดึงตัวเลข
- ผล benchmark เป็น snapshot ตามเวลา ไม่ใช่การรับประกันว่าโมเดลจะตอบเหมือนเดิมทุกครั้ง
- ระบบยังไม่มี local deterministic fast path, response cache หรือ confidence score
- การใช้ `data_collection=deny` เป็น request policy แต่ไม่ใช่การทำให้ OpenRouter กลายเป็น local model

## สิ่งที่จะพัฒนาต่อ

1. เพิ่ม rule-based fast path สำหรับข้อความที่มีรูปแบบชัดเจน เพื่อลด latency และจำนวน API requests
2. ส่งข้อความที่กำกวมไปให้โมเดลเฉพาะเมื่อจำเป็น
3. เพิ่ม retry budget และ circuit breaker เพื่อไม่ให้ระบบรอจน p95 สูงเกินไป
4. เพิ่ม dataset จากข้อมูล anonymized และให้คนตรวจ label
5. เพิ่ม confidence และ human review สำหรับรายละเอียดที่โมเดลไม่มั่นใจ
6. ทดลองโมเดลหรือ provider สำรองเมื่อ free endpoint rate limited

## การรักษาความปลอดภัย

- API key อ่านจาก `OPENROUTER_API_KEY` เท่านั้น
- ไม่ commit key ลง Git
- ไม่เก็บ raw prompt หรือ raw model response ใน evaluation report
- UI ไม่เก็บข้อความและไม่ log request body
- key ที่ใช้ benchmark ถูกยกเลิกหลังการทดสอบ
- ถ้า key เคยถูกส่งใน chat, terminal log หรือ screenshot ให้ถือว่าเปิดเผยแล้วและต้อง revoke ทันที

## ประวัติการพัฒนาใน Git

ชื่อ branch สื่อความหมายของงานแต่ละช่วง:

1. `assignment-1/contract-scaffold` — วาง schema, CLI และ contract tests
2. `assignment-1/dataset-validation` — เพิ่ม dataset และ validation
3. `assignment-1/openrouter-provider` — เพิ่ม client, prompt และ fallback
4. `assignment-1/evaluation` — เพิ่ม metrics, latency, cost และ failure taxonomy
5. `assignment-1/local-demo-ui` — เพิ่มหน้า UI สำหรับทดลองใช้งาน

ทุกช่วงมี commit แยกและสามารถย้อนดูแนวคิดการพัฒนาได้ โดย `main` คือเวอร์ชันรวมสำหรับส่งงาน

## เวลาที่ใช้

เวลารวมประมาณ 4.5 ชั่วโมง:

- วาง contract และ project setup: 30 นาที
- ออกแบบ dataset และ validation: 45 นาที
- เชื่อม OpenRouter และทำ prompt: 60 นาที
- ทำ evaluation harness และ backoff: 60 นาที
- ทำ tests และ documentation: 45 นาที
- ทำ benchmark, report และตรวจ security: 30 นาที
- ทำ local demo UI และทดสอบ desktop/mobile: รวมอยู่ในช่วง implementation และ documentation

## ขอบเขตของงาน

โปรเจกต์นี้ตั้งใจทำให้เล็กและอธิบายได้ จุดประสงค์คือแสดงวิธีคิดตั้งแต่กำหนด contract, เตรียม dataset, เชื่อมโมเดล, validate output, วัดผล และรับมือ failure ไม่ใช่การสร้างแอปจัดการการเงินเต็มรูปแบบ
