"""Scoring functions for moat and scalability analysis."""
import re
from pathlib import Path
from typing import Any

import yaml


def load_lexicons() -> dict[str, Any]:
    """Load scoring lexicons from YAML configuration."""
    config_path = Path(__file__).parent.parent.parent / "config" / "scoring_lexicons.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def calculate_moat_score(title: str, abstract: str | None, keywords: list[str] | None) -> tuple[float, dict]:
    """
    Calculate moat score based on barriers to replication.
    
    Returns:
        Tuple of (score, evidence) where score is in [0, 1] and evidence contains details
    """
    lexicons = load_lexicons()
    moat_barriers = lexicons.get("moat_barriers", {})
    
    # Combine all text for analysis
    text = (title or "").lower()
    if abstract:
        text += " " + abstract.lower()
    if keywords:
        text += " " + " ".join(keywords).lower()
    
    # Count barrier types detected
    evidence = {
        "equipment_barriers": [],
        "process_barriers": [],
        "material_barriers": [],
        "compute_barriers": [],
        "openness_signals": [],
    }
    
    total_barriers = 0
    
    # Equipment barriers
    for keyword in moat_barriers.get("equipment", []):
        if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', text):
            evidence["equipment_barriers"].append(keyword)
            total_barriers += 1
    
    # Process barriers
    for keyword in moat_barriers.get("process", []):
        if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', text):
            evidence["process_barriers"].append(keyword)
            total_barriers += 1
    
    # Material barriers
    for keyword in moat_barriers.get("materials", []):
        if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', text):
            evidence["material_barriers"].append(keyword)
            total_barriers += 1
    
    # Compute barriers
    for keyword in moat_barriers.get("compute", []):
        if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', text):
            evidence["compute_barriers"].append(keyword)
            total_barriers += 1
    
    # Openness signals (reduce moat)
    openness_count = 0
    for keyword in moat_barriers.get("openness", []):
        if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', text):
            evidence["openness_signals"].append(keyword)
            openness_count += 1
    
    # Calculate raw score
    # More barriers = higher moat score
    # Cap at reasonable thresholds
    barrier_score = min(1.0, total_barriers / 5.0)  # 5+ barriers = max score
    
    # Penalize for openness (open source reduces moat)
    openness_penalty = min(0.3, openness_count * 0.1)  # Max 30% penalty
    
    score = max(0.0, barrier_score - openness_penalty)
    
    evidence["total_barriers"] = total_barriers
    evidence["openness_count"] = openness_count
    evidence["raw_barrier_score"] = barrier_score
    evidence["openness_penalty"] = openness_penalty
    
    return score, evidence


def calculate_scalability_score(title: str, abstract: str | None, keywords: list[str] | None) -> tuple[float, dict]:
    """
    Calculate scalability score based on manufacturing readiness.
    
    Returns:
        Tuple of (score, evidence) where score is in [0, 1] and evidence contains details
    """
    lexicons = load_lexicons()
    scalability_signals = lexicons.get("scalability_signals", {})
    
    # Combine all text for analysis
    text = (title or "").lower()
    if abstract:
        text += " " + abstract.lower()
    if keywords:
        text += " " + " ".join(keywords).lower()
    
    # Count signal types detected
    evidence = {
        "manufacturing_signals": [],
        "economic_signals": [],
        "maturity_signals": [],
        "blocker_signals": [],
    }
    
    positive_signals = 0
    
    # Manufacturing signals
    for keyword in scalability_signals.get("manufacturing", []):
        if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', text):
            evidence["manufacturing_signals"].append(keyword)
            positive_signals += 1
    
    # Economic signals
    for keyword in scalability_signals.get("economic", []):
        if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', text):
            evidence["economic_signals"].append(keyword)
            positive_signals += 1
    
    # Maturity signals
    for keyword in scalability_signals.get("maturity", []):
        if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', text):
            evidence["maturity_signals"].append(keyword)
            positive_signals += 1
    
    # Blocker signals (reduce scalability)
    blocker_count = 0
    for keyword in scalability_signals.get("blockers", []):
        if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', text):
            evidence["blocker_signals"].append(keyword)
            blocker_count += 1
    
    # Calculate raw score
    # More positive signals = higher scalability
    positive_score = min(1.0, positive_signals / 5.0)  # 5+ signals = max score
    
    # Penalize for blockers
    blocker_penalty = min(0.4, blocker_count * 0.15)  # Max 40% penalty
    
    score = max(0.0, positive_score - blocker_penalty)
    
    evidence["positive_signals"] = positive_signals
    evidence["blocker_count"] = blocker_count
    evidence["raw_positive_score"] = positive_score
    evidence["blocker_penalty"] = blocker_penalty
    
    return score, evidence


def normalize_score_zscore(score: float, domain_mean: float, domain_std: float, clip_std: float = 3.0) -> float:
    """
    Normalize a score using z-score normalization with clipping.
    
    Args:
        score: Raw score to normalize
        domain_mean: Mean score in the domain
        domain_std: Standard deviation in the domain
        clip_std: Number of standard deviations to clip at (default 3.0)
    
    Returns:
        Normalized score in approximately [0, 1] range
    """
    if domain_std == 0:
        return 0.5  # If no variance, return neutral score
    
    # Calculate z-score
    z_score = (score - domain_mean) / domain_std
    
    # Clip to prevent extreme values
    z_score = max(-clip_std, min(clip_std, z_score))
    
    # Map to [0, 1] range
    # z-score range [-clip_std, +clip_std] maps to [0, 1]
    normalized = (z_score + clip_std) / (2 * clip_std)
    
    return max(0.0, min(1.0, normalized))


def calculate_attention_gap_score(
    moat_score: float,
    scalability_score: float,
    repo_stars: int,
    link_count: int,
    domain_mean_stars: float,
    domain_std_stars: float,
) -> tuple[float, dict]:
    """
    Calculate attention gap score (quality vs attention mismatch).
    
    Args:
        moat_score: Moat score of the paper
        scalability_score: Scalability score of the paper
        repo_stars: Total stars from linked repositories
        link_count: Number of paper-repo links
        domain_mean_stars: Mean stars in domain
        domain_std_stars: Standard deviation of stars in domain
    
    Returns:
        Tuple of (score, evidence) where score is in [0, 1]
    """
    # Technical quality proxy (average of moat and scalability)
    technical_quality = (moat_score + scalability_score) / 2.0
    
    # Attention proxy (normalized repo stars + link count boost)
    attention_raw = repo_stars + (link_count * 10)  # Each link worth 10 "stars"
    
    # Normalize attention using domain statistics
    if domain_std_stars > 0:
        attention_normalized = normalize_score_zscore(
            attention_raw, domain_mean_stars, domain_std_stars, clip_std=3.0
        )
    else:
        attention_normalized = 0.5
    
    # Gap score: high quality + low attention = high gap
    # Weighted by quality (we only care about gap if quality is high)
    gap = (1.0 - attention_normalized) * technical_quality
    
    evidence = {
        "technical_quality": technical_quality,
        "repo_stars": repo_stars,
        "link_count": link_count,
        "attention_raw": attention_raw,
        "attention_normalized": attention_normalized,
        "gap": gap,
    }
    
    return max(0.0, min(1.0, gap)), evidence


def calculate_network_score(
    authors: list[str] | None,
    coauthor_counts: dict[str, int] | None = None,
) -> tuple[float, dict]:
    """
    Calculate network score based on author collaboration patterns.
    
    Args:
        authors: List of author names for this paper
        coauthor_counts: Optional dict mapping authors to their total coauthor counts
    
    Returns:
        Tuple of (score, evidence) where score is in [0, 1]
    """
    if not authors or len(authors) == 0:
        return 0.0, {"author_count": 0, "avg_centrality": 0.0}
    
    # Simple centrality proxy: number of coauthors per author
    # If coauthor_counts not provided, use author count as proxy
    if coauthor_counts:
        centralities = [coauthor_counts.get(author, 1) for author in authors]
        avg_centrality = sum(centralities) / len(centralities)
        # Normalize: log scale (researchers with 100+ coauthors are very connected)
        import math
        normalized_centrality = math.log1p(avg_centrality) / math.log1p(100)
    else:
        # Fallback: more authors = more connected (simple proxy)
        author_count = len(authors)
        normalized_centrality = min(1.0, author_count / 10.0)  # 10+ authors = max
        avg_centrality = author_count
    
    # Cross-domain bonus: if authors > 5, assume cross-domain collaboration
    cross_domain_bonus = 0.1 if len(authors) > 5 else 0.0
    
    score = min(1.0, normalized_centrality + cross_domain_bonus)
    
    evidence = {
        "author_count": len(authors),
        "avg_centrality": avg_centrality,
        "cross_domain_bonus": cross_domain_bonus,
    }
    
    return max(0.0, min(1.0, score)), evidence


def calculate_composite_score(
    novelty: float,
    momentum: float,
    attention_gap: float,
    moat: float,
    scalability: float,
    network: float,
) -> tuple[float, dict]:
    """
    Calculate composite score from all 6 component scores.
    
    Weights:
        - novelty: 0.25
        - momentum: 0.15
        - attention_gap: 0.20
        - moat: 0.20
        - scalability: 0.15
        - network: 0.05
    
    Synergy bonus: +0.02 per metric >0.7, capped at +0.08
    
    Returns:
        Tuple of (composite_score, metadata)
    """
    # Weighted sum
    weights = {
        "novelty": 0.25,
        "momentum": 0.15,
        "attention_gap": 0.20,
        "moat": 0.20,
        "scalability": 0.15,
        "network": 0.05,
    }
    
    weighted_sum = (
        novelty * weights["novelty"] +
        momentum * weights["momentum"] +
        attention_gap * weights["attention_gap"] +
        moat * weights["moat"] +
        scalability * weights["scalability"] +
        network * weights["network"]
    )
    
    # Synergy bonus: papers that excel in multiple dimensions get a boost
    high_scores = sum(1 for score in [novelty, momentum, attention_gap, moat, scalability, network] if score > 0.7)
    synergy_bonus = min(0.08, high_scores * 0.02)
    
    composite = weighted_sum + synergy_bonus
    composite = max(0.0, min(1.0, composite))  # Clip to [0, 1]
    
    metadata = {
        "weighted_sum": weighted_sum,
        "synergy_bonus": synergy_bonus,
        "high_score_count": high_scores,
        "weights": weights,
    }
    
    return composite, metadata
