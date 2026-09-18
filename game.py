from datetime import datetime
from zoneinfo import ZoneInfo

from wonderwords import RandomWord

import tslog
from stubs import determine_question_state, select_best_noun

MAX_QUESTIONS = 20
MAX_QUESTION_LENGTH = 500
NOUN_POOL_SIZE = 40

EASTERN = ZoneInfo("America/New_York")

DAILY_WORDS = [
        "leopard", "AI", "passport", "hackathon", "banjo", "cherry", "candy",
        "cave", "coral", "daisy", "octopus", "wolf", "PCB", "star", "bank",
        "chair", "dollar bill", "laundry machine", "car", "tulip"
]


class GameSession:
    def __init__(self):
        self.log = tslog.RequestLog()
        tslog.use(self.log)
        self.candidates = RandomWord().random_words(
            NOUN_POOL_SIZE, include_categories=["nouns"]
        )
        self.noun: str | None = None
        self.questions_asked = 0
        self.over = False
        self.previous_questions = []
        self.mode: str | None = None

    def set_mode(self, mode: str) -> dict:
        if self.questions_asked > 0:
            return {"type": "error", "message": "mode must be set before asking"}
        if mode not in ("daily-mode", "endless-mode"):
            return {"type": "error", "message": f"unknown mode: {mode}"}
        self.mode = mode
        return {"type": "ack", "mode": mode}

    def daily_word(self) -> str:
        today = datetime.now(EASTERN).date()
        day_index = today.toordinal() % len(DAILY_WORDS)
        return DAILY_WORDS[day_index]

    def _ensure_noun(self) -> str:
        if self.noun is None:
            if self.mode == "daily-mode":
                self.noun = self.daily_word()
            else:
                self.noun = select_best_noun(self.candidates)
        return self.noun

    def ask(self, question: str) -> dict:
        if self.over:
            return {"type": "error", "message": "game already over"}

        noun = self._ensure_noun()
        state, guess = determine_question_state(question, noun, self.previous_questions)
        self.questions_asked += 1
        self.previous_questions.append(question)

        if guess == "guessed it":
            self.over = True
            return {"type": "success", "noun": noun, "log": self.log.as_list()}

        if self.questions_asked >= MAX_QUESTIONS:
            self.over = True
            return {"type": "fail", "noun": noun, "log": self.log.as_list()}

        return {"type": "answer", "answer": state}

    def give_up(self) -> dict:
        self.over = True
        return {"type": "fail", "noun": self._ensure_noun(), "log": self.log.as_list()}
