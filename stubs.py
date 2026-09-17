from typing import Literal, Sequence

import tslog
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

AnswerState = Literal["yes", "no", "maybe"]
GuessState = Literal["guessed it", "did not guess it", "not precise enough"]


def select_best_noun(candidates: Sequence[str]) -> str:
    """Pick the best secret noun from candidates."""
    state = {}
    questions = {
        "best_noun": Choice(
            instructions="Which word would be the easiest to guess? Normally easy to guess words are physical concrete things that are common.",
            criteria={noun: None for noun in candidates},
        ),
    }

    with TypeSafeClient() as client:
        response = client.system_one(state=state, questions=questions)
    tslog.record("select_best_noun", {"state": state, "questions": questions}, response)
    print(response.answers["best_noun"].choice)
    return response.answers["best_noun"].choice


def determine_question_state(
    question: str, noun: str, previous_questions: Sequence[str]
) -> tuple[AnswerState, GuessState]:
    state = {
        "secret_word": noun,
        "previous_questions": previous_questions,
        "state": "This is 20 questions, answer the question pertaining to the secret word!",
        "user_question": question
    }
    questions = {
        "question_result": Choice(
            instructions="Is the answer yes?",
            criteria={"yes": None, "no": None, "maybe": None},
        ),
        "game_done": Choice(
            instructions="Does the user know exactly what the item is?",
            criteria={
                "guessed it": "The user has said a direct synonym or has guessed the word",
                "not precise enough": "The user is close but isn't precise enough",
                "did not guess it": "The user is not close, not has figured it out",
            },
        ),
    }
    with TypeSafeClient() as client:
        response = client.system_one(state=state, questions=questions)
    tslog.record("determine_question_state", {"state": state, "questions": questions}, response)
    return (
        response.answers["question_result"].choice,
        response.answers["game_done"].choice,
    )
