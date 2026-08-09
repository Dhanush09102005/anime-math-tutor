def next_difficulty(current_difficulty: int, streak: int, was_correct: bool,
                     min_difficulty: int = 1, max_difficulty: int = 10) -> int:
    """
    Pure function — no side effects, no DB access.
    Decides the difficulty for the NEXT problem based on current state.

    Args:
        current_difficulty: difficulty of the problem just answered
        streak: current correct-answer streak (BEFORE this answer is factored in
                 by the caller — see note below)
        was_correct: whether the most recent answer was correct
        min_difficulty / max_difficulty: clamp bounds

    Returns:
        int — the difficulty to use for the next generated problem
    """
    if was_correct:
        # Ramp up faster the longer the streak goes —
        # rewards sustained correctness, not just a single lucky answer
        if streak >= 5:
            step = 2
        elif streak >= 3:
            step = 1
        else:
            step = 0  # first couple of correct answers don't bump difficulty yet
        new_difficulty = current_difficulty + step
    else:
        # Wrong answer — drop difficulty by 1, but don't spiral down instantly.
        # A single miss shouldn't undo a lot of progress.
        new_difficulty = current_difficulty - 1

    return max(min_difficulty, min(max_difficulty, new_difficulty))