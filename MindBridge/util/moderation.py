from better_profanity import profanity

profanity.load_censor_words()

def contains_bad_words(text: str) -> bool:
    return profanity.contains_profanity(text)


def clean_text(text: str) -> str:
    return profanity.censor(text)