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
