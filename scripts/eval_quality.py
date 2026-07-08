import os
import sys
import json
import time
import re
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Add root directory to python path to import main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main
from langchain_groq import ChatGroq

def extract_json(text: str) -> dict:
    """Robust utility to extract and parse the first JSON block from text, supporting nested JSON."""
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        json_str = text[start:end+1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Could not parse valid JSON from text: {text}")

def evaluate_case(judge_llm, question: str, context_text: str, generated_answer: str) -> dict:
    """Uses LLM-as-a-judge to evaluate faithfulness, answer relevancy, and context precision."""
    prompt = (
        "You are an expert RAG evaluator. Evaluate the quality of a chatbot's response based on the User Question, the retrieved Context, and the Generated Answer.\n\n"
        "Evaluate three specific metrics:\n"
        "1. **Faithfulness**: Rate from 0.0 to 1.0 whether the Generated Answer is grounded *strictly* in the provided Context, without containing any external facts, assumptions, or hallucinations.\n"
        "2. **Answer Relevancy**: Rate from 0.0 to 1.0 how directly and completely the Generated Answer addresses the User Question. If it avoids the question or adds irrelevant fluff, the score should be lower.\n"
        "3. **Context Precision**: Rate from 0.0 to 1.0 how relevant and precise the retrieved Context is for answering the User Question. If the context contains irrelevant noise or is missing key details, the score should be lower.\n\n"
        "Format the output strictly as a JSON object with this exact structure:\n"
        "{\n"
        "  \"faithfulness\": {\"score\": float, \"reason\": \"string\"},\n"
        "  \"answer_relevancy\": {\"score\": float, \"reason\": \"string\"},\n"
        "  \"context_precision\": {\"score\": float, \"reason\": \"string\"}\n"
        "}\n\n"
        "Do not include any pre-text or post-text. Return ONLY the JSON object.\n\n"
        f"User Question: {question}\n\n"
        f"Retrieved Context:\n{context_text}\n\n"
        f"Generated Answer:\n{generated_answer}\n\n"
        "JSON:"
    )

    try:
        response = judge_llm.invoke(prompt)
        result = extract_json(response.content.strip())
        return result
    except Exception as e:
        print(f"Error invoking evaluator LLM: {e}")
        # Default safe fallback values
        return {
            "faithfulness": {"score": 0.0, "reason": f"Evaluation error: {e}"},
            "answer_relevancy": {"score": 0.0, "reason": f"Evaluation error: {e}"},
            "context_precision": {"score": 0.0, "reason": f"Evaluation error: {e}"}
        }

def run_quality_evaluation():
    print("=" * 70)
    print("RUNNING AUTOMATED ANSWER QUALITY EVALUATION (LLM-AS-A-JUDGE)")
    print("=" * 70)

    # 1. Initialize RAG pipeline
    print("Initializing RAG pipeline (this loading step may take a few seconds)...")
    main.setup_rag_pipeline()
    if not main.rag_chain:
        print("Failed to initialize RAG pipeline.")
        sys.exit(1)
    
    # 2. Setup Judge LLM
    judge_llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)

    # 3. Load Q&A dataset
    qa_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "golden_qa.json")
    with open(qa_path, "r", encoding="utf-8") as f:
        qa_pairs = json.load(f)

    results = []
    total_faithfulness = 0.0
    total_relevancy = 0.0
    total_precision = 0.0

    print(f"Loaded {len(qa_pairs)} golden Q&A pairs. Beginning RAG evaluations...\n")

    for i, pair in enumerate(qa_pairs, 1):
        q_id = pair["id"]
        source = pair["source_doc"]
        question = pair["question"]
        ideal = pair["ideal_answer"]

        print(f"[{i}/{len(qa_pairs)}] Question: \"{question}\" (Source: {source})")

        # 4. Generate answer and get context using the active pipeline
        response = main.rag_chain.invoke({
            "input": question,
            "customer_name": "Test Customer",
            "order_id": "ORD-9921",
            "chat_history": []
        })

        generated_answer = response["answer"]
        context_docs = response.get("context", [])
        context_text = "\n---\n".join([doc.page_content for doc in context_docs])

        # 5. Evaluate the response
        eval_scores = evaluate_case(judge_llm, question, context_text, generated_answer)

        # Update totals
        f_score = eval_scores.get("faithfulness", {}).get("score", 0.0)
        r_score = eval_scores.get("answer_relevancy", {}).get("score", 0.0)
        p_score = eval_scores.get("context_precision", {}).get("score", 0.0)

        total_faithfulness += f_score
        total_relevancy += r_score
        total_precision += p_score

        # Log results
        print(f"      -> Faithfulness: {f_score:.2f} | Relevancy: {r_score:.2f} | Precision: {p_score:.2f}")
        
        results.append({
            "id": q_id,
            "question": question,
            "ideal_answer": ideal,
            "generated_answer": generated_answer,
            "source_doc": source,
            "metrics": eval_scores
        })
        time.sleep(1.0) # Rate limit delay between queries to avoid Groq rate limits

    num_cases = len(qa_pairs)
    avg_faithfulness = total_faithfulness / num_cases
    avg_relevancy = total_relevancy / num_cases
    avg_precision = total_precision / num_cases

    print("\n" + "=" * 70)
    print("QUALITY EVALUATION SUMMARY")
    print("=" * 70)
    print(f"Total Test Cases Evaluated: {num_cases}")
    print(f"Average Faithfulness Score : {avg_faithfulness:.4f} (Goal: >0.85)")
    print(f"Average Answer Relevancy   : {avg_relevancy:.4f} (Goal: >0.85)")
    print(f"Average Context Precision  : {avg_precision:.4f} (Goal: >0.85)")
    print("=" * 70)

    # Output detailed metrics report file
    output_report = {
        "summary": {
            "total_cases": num_cases,
            "average_faithfulness": avg_faithfulness,
            "average_relevancy": avg_relevancy,
            "average_context_precision": avg_precision
        },
        "results": results
    }
    
    report_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "quality_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(output_report, f, indent=2)
    print(f"Detailed quality report saved to: data/quality_report.json\n")

if __name__ == "__main__":
    run_quality_evaluation()
