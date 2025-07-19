document.addEventListener("DOMContentLoaded", () => {
  const chatForm = document.getElementById("chat-form");
  const userInput = document.getElementById("user-input");
  const chatBox = document.getElementById("chat-box");
  const sendButton = document.getElementById("send-button");

  // 폼 제출 이벤트 (질문 전송)
  chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const userMessage = userInput.value.trim();
    if (!userMessage) return;

    // 사용자 메시지 화면에 추가
    appendMessage(userMessage, "user-message");
    userInput.value = "";
    userInput.style.height = "auto"; // 높이 초기화

    // 봇 메시지 컨테이너 생성 및 로딩 커서 추가
    const botMessageDiv = appendMessage("", "bot-message");
    const botContentDiv = botMessageDiv.querySelector(".message-content");
    botContentDiv.innerHTML = '<span class="typing-cursor"></span>';

    toggleInput(false);

    try {
      // FastAPI 스트리밍 API에 질문 전송
      const response = await fetch("/api/chat-stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query: userMessage }),
      });

      if (!response.ok) {
        throw new Error(`서버 응답 오류: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullAnswer = "";

      // 로딩 커서 제거
      botContentDiv.innerHTML = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          break;
        }
        fullAnswer += decoder.decode(value, { stream: true });
        botContentDiv.innerHTML = marked.parse(fullAnswer); // 실시간 마크다운 파싱
        scrollToBottom();
      }
    } catch (error) {
      console.error("Error:", error);
      botContentDiv.innerHTML = `<p class="error">죄송합니다. 오류가 발생했습니다.<br>잠시 후 다시 시도해주세요.</p>`;
    } finally {
      scrollToBottom();
      toggleInput(true);
    }
  });

  // 입력창 자동 높이 조절
  userInput.addEventListener("input", () => {
    userInput.style.height = "auto";
    userInput.style.height = `${userInput.scrollHeight}px`;
  });

  // Enter 키로 전송 (Shift + Enter는 줄바꿈)
  userInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      chatForm.dispatchEvent(new Event("submit"));
    }
  });

  // 메시지를 채팅창에 추가하는 함수
  function appendMessage(text, className) {
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${className}`;

    // 아바타 추가
    const avatarDiv = document.createElement("div");
    if (className.includes("user-message")) {
      avatarDiv.className = "user-avatar";
      avatarDiv.textContent = "U";
    } else {
      avatarDiv.className = "bot-avatar";
      const logoDiv = document.createElement("div");
      logoDiv.className = "knou-logo";
      logoDiv.textContent = "KNOU";
      avatarDiv.appendChild(logoDiv);
    }
    messageDiv.appendChild(avatarDiv);

    const contentDiv = document.createElement("div");
    contentDiv.className = "message-content";

    if (className.includes("user-message")) {
      contentDiv.innerHTML = `<p>${text}</p>`;
    } else {
      contentDiv.innerHTML = text; // 초기에는 비어있거나 로딩 상태
    }

    messageDiv.appendChild(contentDiv);
    chatBox.appendChild(messageDiv);
    scrollToBottom();
    return messageDiv;
  }

  // 채팅창을 맨 아래로 스크롤하는 함수
  function scrollToBottom() {
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  // 입력창 활성/비활성 토글 함수
  function toggleInput(enabled) {
    userInput.disabled = !enabled;
    sendButton.disabled = !enabled;
    if (enabled) {
      userInput.focus();
    }
  }
});
