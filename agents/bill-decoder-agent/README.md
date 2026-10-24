# Bill Decoder Agent

> Upload a photo or PDF of any Indian utility bill and get a plain-language explanation of every charge, plus warnings about anything unusual.

**Live demo:** https://bill-decoder-00-14.streamlit.app

---

## Overview

### Problem Statement & Intended Users
- **Problem**: Electricity, water, mobile and broadband bills are full of codes and charges (fixed charges, FAC, tax, arrears, estimated readings) that most people don't understand. So they pay without noticing mistakes, late fees or a sudden jump in usage.
- **Intended Users**: Households, students living away from home, tenants splitting bills, and elderly people who want a simple explanation of what they are paying for.

### Key Features
- **Reads the bill directly**: works with a phone photo (JPG/PNG/WEBP) or a PDF bill.
- **Explains every charge**: lists each line item with a one-line, plain-language meaning.
- **Flags red flags**: late fees, arrears, estimated meter readings, usage spikes, unknown charges or calculation mistakes.
- **Multi-language**: explanation in English, Kannada, Hindi or any language Gemini supports (`--lang`).
- **Money-saving tips**: practical tips specific to the bill type.
- **Two ways to use it**: a command-line tool (`main.py`) and a dark-mode web app (`app.py`) with large text and simple steps, designed for users of all ages.

---

## Technical Stack

- **Language & Runtime**: Python 3.10+
- **Agent Framework / Core Library**: Vanilla script using the `google-genai` SDK; web UI built with Streamlit
- **Models**: Gemini 3.5 Flash (multimodal: reads images and PDFs)
- **External APIs / Tools**: Google Gemini API (Google AI Studio)

---

## Architecture & Data Flow

```
[Bill photo / PDF] --> [main.py] --> reads file bytes + builds prompt
                                         |
                                         v
                                 [Gemini 3.5 Flash]
                                         |
                                         v
[Terminal output] <-- Summary, Charges Explained, Red Flags, Saving Tips
```

`main.py` reads the bill file, detects its type, and sends it along with a structured prompt to Gemini in a single request. The prompt tells the model to use only what is printed on the bill and to say so when something is unreadable, rather than guess.

`app.py` (web app) sends the uploaded bill the same way, but asks Gemini for a JSON response matching a fixed schema (amount, due date, charges, red flags, tips). The page then shows these as cards instead of one long block of text.

---

## Prerequisites

- Python 3.10 or newer
- pip
- A free Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

---

## Installation & Setup

1. **Navigate to the project directory:**
   ```bash
   cd agents/bill-decoder-agent
   ```

2. **Create a virtual environment and install dependencies:**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate

   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   ```bash
   # Linux/macOS:
   cp .env.example .env
   # Windows (PowerShell):
   Copy-Item .env.example .env
   ```
   Open `.env` and replace `your_gemini_api_key_here` with your real key.

---

## Configuration & Environment Variables

| Variable Name | Required | Default | Description |
| :--- | :--- | :--- | :--- |
| `GEMINI_API_KEY` | Yes | *None* | Your Google AI Studio API key |
| `MODEL_NAME` | No | `gemini-3.5-flash` | Gemini model used to read the bill |

---

## How to Run

```bash
# Explain a bill in English
python main.py path/to/bill.jpg

# Explain a PDF bill in Kannada
python main.py path/to/bill.pdf --lang Kannada

# Show help
python main.py --help
```

### Web app

```bash
streamlit run app.py
```

Then open http://localhost:8501, upload a bill, pick a language and press **Explain my bill**.

**Deploying publicly (optional):** the app runs on [Streamlit Community Cloud](https://share.streamlit.io). Set the main file to `agents/bill-decoder-agent/app.py`, then add `GEMINI_API_KEY = "your_key"` under the app's **Secrets**. Note that every visitor then uses your API quota.

---

## Example Input & Output

### Example Input
A phone photo of a real BESCOM electricity bill (not included in the repo for privacy):
```
python main.py "bescom bill.jpeg"
```

### Example Output
Real output from a test run with `gemini-3.5-flash`:
```
Decoding bescom bill.jpeg ...

Here is a simple breakdown of your electricity bill:

### 1. BILL SUMMARY
* Type of Bill & Provider: Electricity Bill (BESCOM, Bangalore – LT1 Tariff)
* Billing Period: 01/04/2025 to 01/05/2025 (1 month)
* Total Amount to Pay: ₹ 0.00 (Your net bill shows -₹ 498.00, which means you
  have an advance balance/credit of ₹ 498.00 with the department).
* Due Date: 15/05/2025

### 2. CHARGES EXPLAINED
* Fixed Charges (₹ 145.00): A standard monthly base fee charged for maintaining
  your power connection.
* Energy Charges (₹ 133.40): The cost of the 23 units of electricity you
  consumed this month (at ₹ 5.80 per unit).
* FPPCA Charges (₹ 6.90): A variable charge for adjustments in fuel and power
  purchase costs.
* P & G Surcharge (GOK Portion) (₹ 8.28): A state government surcharge applied
  to your power usage.
* Tax @ 9.0% (₹ 12.01): Government electricity tax added to your subtotal.
* Gruha Jyothi Subsidy (-₹ 305.59): A 100% government discount covering all
  your current usage and taxes because your consumption (23 units) is within
  your free limit (60 units).
* Interest (₹ 21.15): A small interest fee charged on past delayed payments or
  outstanding dues.
* Arrears (-₹ 519.00): An advance credit from previous excess payments, which
  offsets any current minor fees and leaves you with a negative balance.

### 3. RED FLAGS
* Interest Charge: An interest amount of ₹ 21.15 is added to your bill, which
  suggests there was a delayed payment or pending balance in a previous cycle.
* Security Deposit Notice: The bill includes a note stating that an ASD
  (Additional Security Deposit) of ₹ 260 needs to be paid if you haven't paid
  it already.

### 4. MONEY-SAVING TIPS
1. Stay Within Your Entitlement Limit: Your maximum free entitlement is 60
   units. Since you used only 23 units this month, your entire electricity
   charge was subsidized under the Gruha Jyothi Scheme. Keep your monthly usage
   under 60 units to keep paying ₹ 0 for power consumption.
2. Clear Any Pending Security Deposits: Check if the ₹ 260 ASD is still pending
   and pay it on time to avoid extra interest or penal charges on future bills.
```

---

## How to Test

1. Take a clear photo of any recent utility bill (or download the PDF from your provider's website).
2. Run `python main.py <your-bill-file>`.
3. Check that the output contains all four sections and that the total amount and due date match the bill.
4. Try `--lang Kannada` (or Hindi) and confirm the output is in that language.
5. Error handling checks:
   - Run with a missing file → should print `Error: file not found`.
   - Run with a `.txt` file → should print `Unsupported file type`.
   - Run without a `.env` file → should print `GEMINI_API_KEY is not set`.

---

## Known Limitations

- Accuracy depends on photo quality; blurry, dark or cropped photos may be read incorrectly.
- Usage-spike detection only works if the bill itself prints previous months' usage.
- It explains what is printed on the bill; it does not check official tariff rates from the provider.
- Free-tier Gemini API rate limits apply. During high demand Gemini may return a "model is busy" (503) error; wait a minute and retry, or set a different model with `MODEL_NAME` in `.env`.
- New Google AI Studio keys starting with `AQ.` were rejected by the Gemini API during testing (`401 ACCESS_TOKEN_TYPE_UNSUPPORTED`). A standard `AIza...` key from the Google Cloud Console **APIs & Services → Credentials** page worked.
- Tested on Windows; Linux/macOS should work but are untested.
- This is an informational aid, not financial or legal advice. Always confirm disputes with your provider.

---

## Security & Privacy Considerations

- **Secrets Handling**: The API key is loaded from a local `.env` file, which is excluded by `.gitignore`. It is never hard-coded.
- **Data Privacy**: The bill image is sent to the Google Gemini API for processing. Bills contain personal details (name, address, account number), so review [Google's Gemini API terms](https://ai.google.dev/gemini-api/terms) before use. Nothing is stored locally by this tool.
- **Safety**: The agent does not execute any code or shell commands; it only reads the given file and prints text.

---

## Future Improvements

- [ ] Compare two bills (this month vs last month) side by side.
- [ ] Simple web UI with drag-and-drop upload (Streamlit / Gradio).
- [ ] Check charges against official BESCOM/BWSSB tariff tables.
- [ ] Split a shared bill fairly among roommates.

---

## License

*This project is contributed under the repository's open-source license.*
