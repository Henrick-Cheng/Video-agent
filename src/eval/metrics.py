"""
Evaluation metrics for video question answering.

Targets standard benchmarks: NExT-QA, ActivityNet-QA, MSVD-QA.
"""

from __future__ import annotations


def exact_match(prediction: str, reference: str) -> float:
    """Binary exact match (case- and whitespace-insensitive)."""
    return float(prediction.strip().lower() == reference.strip().lower())


def contains_match(prediction: str, reference: str) -> float:
    """1.0 if reference is a substring of prediction (case-insensitive)."""
    return float(reference.strip().lower() in prediction.strip().lower())


def wup_similarity(word1: str, word2: str) -> float:
    """
    Wu-Palmer similarity between two words using WordNet.
    Returns 0.0 if either word is not found in WordNet.

    Requires: pip install nltk; python -m nltk.downloader wordnet
    """
    # TODO: implement with NLTK
    #
    # from nltk.corpus import wordnet
    # synsets1 = wordnet.synsets(word1)
    # synsets2 = wordnet.synsets(word2)
    # if not synsets1 or not synsets2:
    #     return 0.0
    # return max(s1.wup_similarity(s2) or 0.0
    #            for s1 in synsets1 for s2 in synsets2)
    raise NotImplementedError("Install nltk and download wordnet first.")


def evaluate_qa(
    predictions: list[dict],
    references: list[dict],
    metric: str = "exact_match",
) -> dict:
    """
    Evaluate a list of QA predictions against ground-truth references.

    Parameters
    ----------
    predictions : [{"question_id": str, "answer": str}, ...]
    references  : [{"question_id": str, "answer": str}, ...]
    metric      : "exact_match" | "contains_match"

    Returns
    -------
    {"score": float, "count": int, "metric": str}
    """
    score_fn = {"exact_match": exact_match, "contains_match": contains_match}[metric]
    ref_map = {r["question_id"]: r["answer"] for r in references}

    scores = []
    for pred in predictions:
        ref = ref_map.get(pred["question_id"])
        if ref is not None:
            scores.append(score_fn(pred["answer"], ref))

    return {
        "score":  round(sum(scores) / len(scores), 4) if scores else 0.0,
        "count":  len(scores),
        "metric": metric,
    }
