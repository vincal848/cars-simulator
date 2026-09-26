"""Word wrapping for pygame fonts."""

import pygame


def wrap(text: str, font: pygame.font.Font, width: int) -> list[str]:
    """Split ``text`` into lines no wider than ``width``; newlines start new paragraphs."""
    lines = []
    for paragraph in text.split("\n"):
        line = ""
        for word in paragraph.split():
            if line and font.size(line + " " + word)[0] > width:
                lines.append(line)
                line = word
            else:
                line = (line + " " + word).strip()
        lines.append(line)
    return lines


def wrap_breaking_words(text: str, font: pygame.font.Font, width: int) -> list[str]:
    """Like :func:`wrap`, but also splits single words (such as long IDs) that are too wide."""
    lines = []
    for paragraph in text.split("\n"):
        line = ""
        for word in paragraph.split():
            for chunk in _split_word(word, font, width):
                if line and font.size(line + " " + chunk)[0] > width:
                    lines.append(line)
                    line = chunk
                else:
                    line = (line + " " + chunk).strip()
        lines.append(line)
    return lines


def _split_word(word: str, font: pygame.font.Font, width: int) -> list[str]:
    chunks = []
    while font.size(word)[0] > width:
        count = 1
        while count < len(word) and font.size(word[: count + 1])[0] <= width:
            count += 1
        chunks.append(word[:count])
        word = word[count:]
    chunks.append(word)
    return chunks
