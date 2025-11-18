"""Tests for attention gap, network, and composite scoring."""
from app.services.scoring import (
    calculate_attention_gap_score,
    calculate_composite_score,
    calculate_network_score,
)


class TestAttentionGapScore:
    """Tests for attention gap score calculation."""
    
    def test_high_quality_low_attention(self):
        """Test high quality + low attention = high gap."""
        score, evidence = calculate_attention_gap_score(
            moat_score=0.8,
            scalability_score=0.7,
            repo_stars=5,
            link_count=1,
            domain_mean_stars=100.0,
            domain_std_stars=50.0,
        )
        
        # High technical quality (0.75) + low attention = high gap
        assert score > 0.3, "Should have moderate-high gap score"
        assert evidence["technical_quality"] == 0.75
        assert evidence["repo_stars"] == 5
    
    def test_low_quality_low_attention(self):
        """Test low quality + low attention = low gap (not interesting)."""
        score, evidence = calculate_attention_gap_score(
            moat_score=0.2,
            scalability_score=0.3,
            repo_stars=5,
            link_count=1,
            domain_mean_stars=100.0,
            domain_std_stars=50.0,
        )
        
        # Low technical quality means gap is weighted down
        assert score < 0.5, "Low quality should reduce gap score"
        assert evidence["technical_quality"] == 0.25
    
    def test_high_quality_high_attention(self):
        """Test high quality + high attention = low gap (already recognized)."""
        score, _evidence = calculate_attention_gap_score(
            moat_score=0.8,
            scalability_score=0.7,
            repo_stars=500,
            link_count=10,
            domain_mean_stars=100.0,
            domain_std_stars=50.0,
        )
        
        # High attention reduces gap
        assert score < 0.7, "High attention should reduce gap"
    
    def test_zero_variance_handling(self):
        """Test handling of zero standard deviation."""
        score, evidence = calculate_attention_gap_score(
            moat_score=0.5,
            scalability_score=0.5,
            repo_stars=50,
            link_count=2,
            domain_mean_stars=50.0,
            domain_std_stars=0.0,  # Zero variance
        )
        
        # Should not crash
        assert 0.0 <= score <= 1.0
        assert evidence["attention_normalized"] == 0.5


class TestNetworkScore:
    """Tests for network score calculation."""
    
    def test_many_authors(self):
        """Test many authors increases network score."""
        authors = [f"Author {i}" for i in range(15)]
        score, evidence = calculate_network_score(authors)
        
        assert score > 0.5, "Many authors should give high network score"
        assert evidence["author_count"] == 15
        assert evidence["cross_domain_bonus"] > 0
    
    def test_few_authors(self):
        """Test few authors gives lower network score."""
        authors = ["Author 1", "Author 2"]
        score, evidence = calculate_network_score(authors)
        
        assert score < 0.5, "Few authors should give lower network score"
        assert evidence["author_count"] == 2
        assert evidence["cross_domain_bonus"] == 0.0
    
    def test_no_authors(self):
        """Test no authors gives zero score."""
        score, evidence = calculate_network_score(None)
        
        assert score == 0.0
        assert evidence["author_count"] == 0
    
    def test_with_coauthor_counts(self):
        """Test with provided coauthor counts."""
        authors = ["Prolific Author", "New Author"]
        coauthor_counts = {
            "Prolific Author": 50,
            "New Author": 2,
        }
        
        score, evidence = calculate_network_score(authors, coauthor_counts)
        
        assert score > 0.0
        assert evidence["avg_centrality"] == 26.0  # (50 + 2) / 2


class TestCompositeScore:
    """Tests for composite score calculation."""
    
    def test_weighted_sum(self):
        """Test basic weighted sum calculation."""
        score, metadata = calculate_composite_score(
            novelty=0.5,
            momentum=0.5,
            attention_gap=0.5,
            moat=0.5,
            scalability=0.5,
            network=0.5,
        )
        
        # All 0.5, weighted sum should also be 0.5
        assert 0.45 <= score <= 0.55  # Allow for synergy bonus
        assert metadata["weighted_sum"] == 0.5
    
    def test_synergy_bonus(self):
        """Test synergy bonus for high-performing papers."""
        score, metadata = calculate_composite_score(
            novelty=0.8,
            momentum=0.75,
            attention_gap=0.9,
            moat=0.85,
            scalability=0.8,
            network=0.75,  # Changed from 0.7 to be >0.7
        )
        
        # All scores > 0.7, should get max synergy bonus
        assert metadata["high_score_count"] == 6
        assert metadata["synergy_bonus"] > 0.0
        assert score > metadata["weighted_sum"]
    
    def test_no_synergy_bonus(self):
        """Test no synergy bonus for mediocre papers."""
        score, metadata = calculate_composite_score(
            novelty=0.3,
            momentum=0.4,
            attention_gap=0.3,
            moat=0.5,
            scalability=0.4,
            network=0.2,
        )
        
        # No scores > 0.7, no synergy bonus
        assert metadata["high_score_count"] == 0
        assert metadata["synergy_bonus"] == 0.0
        assert score == metadata["weighted_sum"]
    
    def test_clipping(self):
        """Test score is clipped to [0, 1] range."""
        # Artificially high scores
        score, _ = calculate_composite_score(
            novelty=1.0,
            momentum=1.0,
            attention_gap=1.0,
            moat=1.0,
            scalability=1.0,
            network=1.0,
        )
        
        assert score <= 1.0
        
        # Artificially low scores
        score, _ = calculate_composite_score(
            novelty=0.0,
            momentum=0.0,
            attention_gap=0.0,
            moat=0.0,
            scalability=0.0,
            network=0.0,
        )
        
        assert score >= 0.0
    
    def test_weights_sum_to_one(self):
        """Test that weights sum to 1.0."""
        _, metadata = calculate_composite_score(
            novelty=0.5,
            momentum=0.5,
            attention_gap=0.5,
            moat=0.5,
            scalability=0.5,
            network=0.5,
        )
        
        weights = metadata["weights"]
        total_weight = sum(weights.values())
        assert abs(total_weight - 1.0) < 0.001, "Weights should sum to 1.0"
