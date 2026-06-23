import { useEffect, useMemo, useRef, useState } from "react";

import { stripAccents } from "../../utils/foodCategory";
import { sendAiChatMessage } from "../../services/apiService";
import "./NutriGainChatbot.css";

const DEFAULT_QUESTIONS = [
  "Hôm nay tôi nên ăn thêm gì?",
  "Protein là gì?",
  "Tôi nên ăn món nào giàu protein?",
  "Protein hôm nay của tôi đủ chưa?",
  "Tại sao ngủ quan trọng?",
  "Tăng cân lành mạnh là gì?",
];

const GREETING = {
  id: "greeting",
  role: "assistant",
  text: "Chào bạn, mình là Trợ lý NutriGain. Bạn có thể hỏi mình về thực đơn hôm nay, bữa phụ, protein, giấc ngủ hoặc cách tăng cân lành mạnh.",
};

const FALLBACK_API_ERROR = "Mình chưa trả lời được lúc này. Bạn thử hỏi lại sau nhé.";
const FALLBACK_EMPTY_ANSWER = "Mình chưa có câu trả lời phù hợp. Bạn thử hỏi lại theo cách khác nhé.";

const LOCAL_FALLBACK_ANSWERS = [
  {
    test: (q) => /protein\s+la\s+gi|protein\s*là\s*gì|chat\s+dam|chất\s+đạm/i.test(q),
    answer:
      "Protein, hay còn gọi là chất đạm, là chất giúp cơ thể phục hồi và xây dựng mô cơ. Với người muốn tăng cân lành mạnh, protein rất quan trọng vì giúp tăng cân có chất, không chỉ tăng thêm calo.\n\nBạn có thể bổ sung protein từ trứng, sữa, thịt, cá, đậu hũ, đậu, sữa chua hoặc các loại hạt.",
  },
  {
    test: (q) => /mon\s+nao\s+giau\s+protein|món\s+nào\s+giàu\s+protein|an\s+gi\s+de\s+du\s+dam|ăn\s+gì\s+để\s+đủ\s+đạm/i.test(q),
    answer:
      "Bạn có thể chọn các món dễ ăn như trứng, sữa, sữa chua, thịt gà, thịt bò, cá, đậu hũ hoặc các loại đậu. Nếu đang tăng cân, hãy thêm một nguồn protein vào mỗi bữa chính.",
  },
  {
    test: (q) => /protein\s+hom\s+nay\s+du\s+chua|protein\s+hôm\s+nay\s+đủ\s+chưa/i.test(q),
    answer:
      "Nếu bạn đã có thực đơn hôm nay, mình có thể dựa vào tổng protein trong thực đơn để nhận xét. Nếu chưa có thực đơn, hãy tạo thực đơn trước để NutriGain tính protein chính xác hơn.",
  },
  {
    test: (q) => /tang\s+can\s+lanh\s+manh|tăng\s+cân\s+lành\s+mạnh/i.test(q),
    answer:
      "Tăng cân lành mạnh là tăng từ từ, ăn đủ năng lượng, đủ đạm và duy trì thói quen sinh hoạt ổn định. Mục tiêu không phải là ăn thật nhiều trong một lúc, mà là giúp cơ thể hấp thu tốt và khỏe hơn.",
  },
  {
    test: (q) => /tai\s+sao\s+ngu\s+quan\s+trong|tại\s+sao\s+ngủ\s+quan\s+trọng|giac\s+ngu|giấc\s+ngủ/i.test(q),
    answer:
      "Ngủ đủ giúp cơ thể phục hồi, giảm mệt và duy trì nhịp ăn uống đều hơn. Khi ngủ tốt, cơ thể cũng có điều kiện hấp thu và phục hồi tốt hơn.",
  },
];

function toText(value) {
  return String(value || "").replace(/\r\n/g, "\n").trim();
}

function normalizeVietnamese(value) {
  return stripAccents(toText(value)).toLowerCase().replace(/[_/]+/g, " ").replace(/\s+/g, " ").trim();
}

function detectChatIntent(message) {
  const text = normalizeVietnamese(message);

  const asksProtein = /\bprotein\b|\bdam\b/.test(text);
  const asksToday = /hom nay|cua toi|của tôi|du chua|đủ chưa|thieu|thiếu|muc tieu|mục tiêu|bao nhieu|bao nhiêu|ong chua|ổn chưa|thuc don hom nay|thực đơn hôm nay/.test(text);

  if (asksProtein && asksToday) return "protein_status";

  if (
    asksProtein &&
    (/la gi|là gì|tac dung|tác dụng|giup gi|giúp gì|protein la gi|protein là gì|dam la gi|đạm là gì/.test(text) || text === "protein" || text === "dam")
  ) {
    return "protein_concept";
  }

  if (/tang can lanh manh|tăng cân lành mạnh|tai sao ngu quan trong|tại sao ngủ quan trọng/.test(text)) {
    return "concept_general";
  }

  if (/hom nay|cua toi|của tôi|du chua|đủ chưa|thieu|thiếu|muc tieu|mục tiêu|bao nhiêu|bao nhieu|thuc don hom nay|thực đơn hôm nay|an vay on chua|ăn vậy ổn chưa/.test(text)) {
    return "personal_status";
  }

  return "general";
}

function pickLocalFallbackAnswer(questionText) {
  const question = normalizeVietnamese(questionText);
  const matched = LOCAL_FALLBACK_ANSWERS.find((item) => item.test(question));
  return matched?.answer || "";
}

function getNutritionSnapshot({ summary, validation, consumedNutrition, meals, nutritionTarget, currentPlan }) {
  const totalCalories = Number(
    validation?.totalCalories ??
      validation?.totalKcal ??
      validation?.total_kcal ??
      summary?.eatenCalories ??
      consumedNutrition?.calories ??
      currentPlan?.meal_plan?.total_kcal ??
      0,
  );
  const targetCalories = Number(
    validation?.targetKcal ??
      validation?.target_kcal ??
      summary?.targetCalories ??
      nutritionTarget?.targetCalories ??
      currentPlan?.nutrition_target?.calorie_target ??
      currentPlan?.target?.calories ??
      0,
  );
  const totalProtein = Number(
    validation?.totalProtein ??
      validation?.total_protein ??
      currentPlan?.meal_plan?.total_protein_g ??
      summary?.protein ??
      consumedNutrition?.protein ??
      0,
  );
  const targetProtein = Number(
    validation?.targetProtein ??
      validation?.target_protein ??
      summary?.protein ??
      nutritionTarget?.proteinTarget ??
      currentPlan?.nutrition_target?.protein_g ??
      currentPlan?.target?.protein ??
      0,
  );

  return {
    totalCalories,
    targetCalories,
    totalProtein,
    targetProtein,
    hasMeals: Array.isArray(meals) ? meals.length > 0 : Boolean(currentPlan?.meal_plan),
  };
}

function buildProteinConceptAnswer() {
  return "Protein, hay còn gọi là chất đạm, là chất giúp cơ thể phục hồi và xây dựng mô cơ. Với người muốn tăng cân lành mạnh, protein quan trọng vì nó giúp tăng cân 'có chất', không chỉ tăng thêm calo.\n\nBạn có thể bổ sung protein từ trứng, sữa, thịt, cá, đậu hũ, các loại đậu, sữa chua hoặc các loại hạt.";
}

function buildProteinStatusAnswer(snapshot) {
  if (!snapshot.hasMeals || !(snapshot.targetProtein > 0)) {
    return "Hiện mình chưa có đủ dữ liệu protein hôm nay để kết luận. Bạn hãy tạo thực đơn hôm nay trước, NutriGain sẽ tính tổng protein và so với mục tiêu của bạn.";
  }

  const diff = Math.round(snapshot.totalProtein - snapshot.targetProtein);
  if (diff >= 0) {
    return `Hôm nay protein của bạn đã đạt mục tiêu. Bạn đang có khoảng ${Math.round(snapshot.totalProtein)}g protein so với mục tiêu ${Math.round(snapshot.targetProtein)}g. Hãy duy trì ăn đều và uống đủ nước nhé.`;
  }

  return `Hôm nay bạn còn thiếu khoảng ${Math.abs(diff)}g protein so với mục tiêu. Bạn có thể bổ sung thêm trứng, sữa, thịt gà, cá, đậu hũ hoặc sữa chua vào bữa gần nhất.`;
}

function buildKcalStatusAnswer(snapshot) {
  if (!snapshot.hasMeals || !(snapshot.targetCalories > 0)) {
    return "Hiện mình chưa có thực đơn hôm nay để tính năng lượng. Bạn hãy tạo thực đơn trước để NutriGain kiểm tra chính xác hơn.";
  }

  const diff = Math.round(snapshot.totalCalories - snapshot.targetCalories);
  if (diff >= 0) {
    return `Hôm nay thực đơn của bạn đã đạt mục tiêu năng lượng. Bạn đang có khoảng ${Math.round(snapshot.totalCalories)} kcal so với mục tiêu ${Math.round(snapshot.targetCalories)} kcal. Hãy duy trì ăn đều và uống đủ nước nhé.`;
  }

  return `Hôm nay bạn còn thiếu khoảng ${Math.abs(diff)} kcal so với mục tiêu. Bạn có thể thêm 1 ly sữa, 1 hũ sữa chua, 1 quả chuối hoặc một ít hạt. Không cần ăn quá nhiều, chỉ cần thêm một món nhỏ là đủ.`;
}

function buildPersonalStatusAnswer(messageText, context) {
  const snapshot = getNutritionSnapshot(context);
  const text = normalizeVietnamese(messageText);

  if (/protein/.test(text) || /dam/.test(text)) {
    return buildProteinStatusAnswer(snapshot);
  }

  if (/kcal|calo|nang luong|năng lượng/.test(text)) {
    return buildKcalStatusAnswer(snapshot);
  }

  if (/thuc don|thực đơn|an vay on chua|ăn vậy ổn chưa|hom nay|hôm nay|thieu|thiếu/.test(text)) {
    const kcalDiff = Math.round(snapshot.totalCalories - snapshot.targetCalories);
    const proteinDiff = Math.round(snapshot.totalProtein - snapshot.targetProtein);

    if (!snapshot.hasMeals || !(snapshot.targetCalories > 0) || !(snapshot.targetProtein > 0)) {
      return "Hiện mình chưa có đủ dữ liệu thực đơn hôm nay để nhận xét. Bạn hãy tạo thực đơn trước để NutriGain kiểm tra kcal và protein chính xác hơn.";
    }

    if (kcalDiff < 0 && proteinDiff < 0) {
      return `Hôm nay thực đơn của bạn còn thiếu khoảng ${Math.abs(kcalDiff)} kcal và ${Math.abs(proteinDiff)}g protein so với mục tiêu. Bạn có thể thêm một món nhỏ giàu đạm như trứng, sữa chua, sữa hoặc đậu hũ.`;
    }

    if (kcalDiff < 0) {
      return `Hôm nay bạn còn thiếu khoảng ${Math.abs(kcalDiff)} kcal so với mục tiêu. Bạn có thể bổ sung nhẹ bằng 1 ly sữa, 1 hũ sữa chua, 1 quả chuối hoặc một ít hạt.`;
    }

    if (proteinDiff < 0) {
      return `Hôm nay bạn còn thiếu khoảng ${Math.abs(proteinDiff)}g protein so với mục tiêu. Bạn có thể thêm trứng, sữa, thịt gà, cá, đậu hũ hoặc sữa chua vào bữa gần nhất.`;
    }

    return `Hôm nay thực đơn của bạn đã khá ổn. Bạn đang có khoảng ${Math.round(snapshot.totalCalories)} kcal và ${Math.round(snapshot.totalProtein)}g protein so với mục tiêu. Hãy duy trì ăn đều và uống đủ nước nhé.`;
  }

  return FALLBACK_EMPTY_ANSWER;
}

function extractAnswerFromResponse(data) {
  const answerCandidates = [
    data?.answer,
    data?.message,
    data?.reply,
    data?.data?.answer,
    data?.data?.message,
    data?.data?.reply,
    data?.result?.answer,
    data?.result?.message,
    data?.result?.reply,
  ];
  const first = answerCandidates.find((value) => typeof value === "string" && value.trim().length > 0);
  return toText(first);
}

function looksTruncated(answer) {
  const text = toText(answer);
  if (!text) return false;
  return text.endsWith("...") || text.endsWith("…") || text.length < 36;
}

function isLikelyIncompleteAnswer(answer) {
  const text = toText(answer);
  if (!text) return true;
  if (looksTruncated(text)) return true;

  const lower = text.toLowerCase();
  const danglingEndings = [
    "để",
    "để bạn",
    "để có",
    "để giúp",
    "để bổ sung",
    "và",
    "hoặc",
    "nhưng",
    "because",
    "to",
    "for",
  ];
  if (danglingEndings.some((ending) => lower.endsWith(ending))) {
    return true;
  }

  const hasClosingPunctuation = /[.!?…]$/.test(text);
  if (!hasClosingPunctuation && text.length < 150) {
    return true;
  }

  return false;
}

function extractNumberFromText(text, metric) {
  const safe = toText(text);
  if (!safe) return null;
  const regex = metric === "protein"
    ? /(thiếu\s+khoảng\s+|thiếu\s+)(\d+(?:[.,]\d+)?)\s*g\b/i
    : /(thiếu\s+khoảng\s+|thiếu\s+)(\d+(?:[.,]\d+)?)\s*kcal\b/i;
  const match = safe.match(regex);
  if (!match?.[2]) return null;
  const normalized = Number(match[2].replace(",", "."));
  return Number.isFinite(normalized) ? Math.round(normalized) : null;
}

function buildContextualNutritionFallback(questionText, rawAnswer) {
  const question = toText(questionText).toLowerCase();
  const answer = toText(rawAnswer).toLowerCase();
  const combined = `${question} ${answer}`;
  const indicatesEnough = /đủ|khá ổn|on track|đạt mục tiêu|ổn so với mục tiêu/.test(combined);

  const hasKcalContext = /\bkcal\b|calo|nang luong|năng lượng|an them|ăn thêm|thieu\s+khoang|thiếu\s+khoảng/.test(combined);
  const hasProteinContext = /protein|chất đạm|chat dam|\bđạm\b/.test(combined);

  if (indicatesEnough) {
    return "Hôm nay thực đơn của bạn khá ổn so với mục tiêu. Hãy duy trì ăn đều và uống đủ nước nhé.";
  }

  if (hasKcalContext) {
    const missingKcal = extractNumberFromText(rawAnswer, "kcal");
    if (Number.isFinite(missingKcal) && missingKcal > 0) {
      return `Hôm nay thực đơn của bạn đang thiếu khoảng ${missingKcal} kcal so với mục tiêu.\nBạn có thể bổ sung nhẹ bằng 1 ly sữa, 1 hũ sữa chua, 1 quả chuối hoặc một ít hạt.\nKhông cần ăn quá nhiều, chỉ cần thêm một món nhỏ là đủ.`;
    }
    return "Hôm nay thực đơn của bạn đang thiếu năng lượng so với mục tiêu.\nBạn có thể bổ sung nhẹ bằng 1 ly sữa, 1 hũ sữa chua, 1 quả chuối hoặc một ít hạt.\nKhông cần ăn quá nhiều, chỉ cần thêm một món nhỏ là đủ.";
  }

  if (hasProteinContext) {
    const missingProtein = extractNumberFromText(rawAnswer, "protein");
    if (Number.isFinite(missingProtein) && missingProtein > 0) {
      return `Hôm nay thực đơn của bạn đang thiếu khoảng ${missingProtein}g protein.\nBạn có thể thêm trứng, sữa, thịt gà, cá, đậu hũ hoặc sữa chua vào một bữa gần nhất.`;
    }
    return "Hôm nay thực đơn của bạn có thể chưa đủ protein theo mục tiêu.\nBạn có thể thêm trứng, sữa, thịt gà, cá, đậu hũ hoặc sữa chua vào một bữa gần nhất.";
  }

  return "Hôm nay thực đơn của bạn khá ổn so với mục tiêu. Hãy duy trì ăn đều và uống đủ nước nhé.";
}

function ensureCompleteAnswer(text, questionText) {
  const normalized = toText(text);
  if (!normalized) {
    return FALLBACK_EMPTY_ANSWER;
  }

  if (isLikelyIncompleteAnswer(normalized)) {
    return buildContextualNutritionFallback(questionText, normalized);
  }

  return normalized;
}

function createId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function storageKeyFor(userId) {
  return `nutrigain_chat_messages_${userId || "guest"}`;
}

function loadMessages(userId) {
  if (typeof window === "undefined") return [GREETING];
  try {
    const raw = window.localStorage.getItem(storageKeyFor(userId));
    const parsed = raw ? JSON.parse(raw) : null;
    if (Array.isArray(parsed) && parsed.length > 0) {
      return parsed.slice(-30);
    }
  } catch {
    // Ignore corrupted local chat history.
  }
  return [GREETING];
}

function saveMessages(userId, messages) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(storageKeyFor(userId), JSON.stringify(messages.slice(-30)));
  } catch {
    // Local storage can be unavailable in private browsing modes.
  }
}

export default function NutriGainChatbot({ userId, summary, validation, consumedNutrition, meals, nutritionTarget, currentPlan }) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState(() => loadMessages(userId));
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [conversationId, setConversationId] = useState(null);
  const [suggestedQuestions, setSuggestedQuestions] = useState(DEFAULT_QUESTIONS);
  const messagesEndRef = useRef(null);
  const trimmedInput = input.trim();

  const page = useMemo(() => {
    if (typeof window === "undefined") return "";
    return window.location.pathname || "";
  }, [isOpen]);

  useEffect(() => {
    setMessages(loadMessages(userId));
  }, [userId]);

  useEffect(() => {
    saveMessages(userId, messages);
  }, [messages, userId]);

  useEffect(() => {
    if (!isOpen) return;
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isOpen, isLoading]);

  async function handleSend(text = trimmedInput) {
    const messageText = String(text || "").trim();
    if (!messageText || isLoading) return;

    const intent = detectChatIntent(messageText);
    const context = { summary, validation, consumedNutrition, meals, nutritionTarget, currentPlan };
    if (intent === "protein_concept") {
      const userMessage = { id: createId(), role: "user", text: messageText };
      setMessages((current) => [...current, userMessage].slice(-30));
      setInput("");
      setError("");
      setMessages((current) => [...current, { id: createId(), role: "assistant", text: buildProteinConceptAnswer() }].slice(-30));
      return;
    }

    if (intent === "protein_status" || intent === "personal_status") {
      const userMessage = { id: createId(), role: "user", text: messageText };
      setMessages((current) => [...current, userMessage].slice(-30));
      setInput("");
      setError("");
      setMessages((current) => [...current, { id: createId(), role: "assistant", text: buildPersonalStatusAnswer(messageText, context) }].slice(-30));
      return;
    }

    if (intent === "concept_general") {
      const localAnswer = pickLocalFallbackAnswer(messageText) || FALLBACK_EMPTY_ANSWER;
      const userMessage = { id: createId(), role: "user", text: messageText };
      setMessages((current) => [...current, userMessage].slice(-30));
      setInput("");
      setError("");
      setMessages((current) => [...current, { id: createId(), role: "assistant", text: localAnswer }].slice(-30));
      return;
    }

    const userMessage = { id: createId(), role: "user", text: messageText };
    setMessages((current) => [...current, userMessage].slice(-30));
    setInput("");
    setError("");
    setIsLoading(true);

    try {
      const response = await sendAiChatMessage({
        message: messageText,
        conversation_id: conversationId,
        page,
      });
      console.log("[CHATBOT RAW RESPONSE]", response);
      setConversationId(response?.conversation_id || conversationId);
      if (Array.isArray(response?.suggested_questions) && response.suggested_questions.length > 0) {
        const cleaned = response.suggested_questions
          .map((item) => toText(item))
          .filter(Boolean)
          .slice(0, 8);
        if (cleaned.length > 0) {
          setSuggestedQuestions(cleaned);
        }
      }
      const extractedAnswer = extractAnswerFromResponse(response);
      const localFallbackAnswer = pickLocalFallbackAnswer(messageText);
      const answerBeforeCompleteCheck = extractedAnswer
        ? (looksTruncated(extractedAnswer) && localFallbackAnswer ? localFallbackAnswer : extractedAnswer)
        : (localFallbackAnswer || FALLBACK_EMPTY_ANSWER);
      const finalAnswer = ensureCompleteAnswer(answerBeforeCompleteCheck, messageText);
      console.log("[CHATBOT ANSWER]", {
        intent,
        extractedAnswer,
        answerBeforeCompleteCheck,
        finalAnswer,
      });
      const assistantMessage = {
        id: createId(),
        role: "assistant",
        text: finalAnswer,
      };
      setMessages((current) => [...current, assistantMessage].slice(-30));
    } catch (err) {
      console.error("AI chat error:", err);
      setError(FALLBACK_API_ERROR);
      const localFallbackAnswer = pickLocalFallbackAnswer(messageText);
      const assistantMessage = {
        id: createId(),
        role: "assistant",
        text: localFallbackAnswer || FALLBACK_API_ERROR,
      };
      setMessages((current) => [...current, assistantMessage].slice(-30));
    } finally {
      setIsLoading(false);
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    handleSend();
  }

  return (
    <div className="ng-chatbot" aria-live="polite">
      {isOpen ? (
        <section className="ng-chatbot-panel" aria-label="Trợ lý NutriGain">
          <header className="ng-chatbot-header">
            <div>
              <h2>Trợ lý NutriGain</h2>
              <p>Hỏi về thực đơn, bữa phụ và tăng cân lành mạnh</p>
            </div>
            <button type="button" className="ng-chatbot-close" onClick={() => setIsOpen(false)} aria-label="Đóng trợ lý">
              ×
            </button>
          </header>

          <div className="ng-chatbot-messages">
            {messages.map((message) => (
              <div key={message.id} className={`ng-chatbot-message ${message.role}`}>
                {message.text}
              </div>
            ))}
            {isLoading ? <div className="ng-chatbot-message assistant pending">Trợ lý đang trả lời...</div> : null}
            <div ref={messagesEndRef} />
          </div>

          {error ? <div className="ng-chatbot-error">{error}</div> : null}

          <div className="ng-chatbot-quick">
            {suggestedQuestions.map((question) => (
              <button key={question} type="button" onClick={() => handleSend(question)} disabled={isLoading}>
                {question}
              </button>
            ))}
          </div>

          <form className="ng-chatbot-form" onSubmit={handleSubmit}>
            <input
              value={input}
              maxLength={1000}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Hỏi Trợ lý NutriGain..."
              aria-label="Hỏi Trợ lý NutriGain"
            />
            <button type="submit" disabled={!trimmedInput || isLoading}>
              Gửi
            </button>
          </form>
        </section>
      ) : null}

      <button type="button" className="ng-chatbot-sticker" onClick={() => setIsOpen((value) => !value)} aria-expanded={isOpen} aria-label="Mở trợ lý NutriGain" title="Trợ lý NutriGain">
        <span aria-hidden="true" className="ng-chatbot-sticker-icon">🤖</span>
      </button>
    </div>
  );
}
