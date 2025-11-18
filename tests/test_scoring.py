"""Unit tests for scoring functions."""

from app.services.scoring import (
    calculate_moat_score,
    calculate_scalability_score,
    normalize_score_zscore,
)


class TestMoatScore:
    """Tests for moat score calculation."""
    
    def test_high_moat_with_equipment_barriers(self):
        """Test paper with equipment barriers gets high moat score."""
        title = "Novel Quantum Computing Using Cryogenic Dilution Refrigerator"
        abstract = "We demonstrate a new approach requiring cleanroom fabrication and ultra-high vacuum conditions."
        keywords = ["quantum", "cryogenic"]
        
        score, evidence = calculate_moat_score(title, abstract, keywords)
        
        assert score > 0.5, "Should have high moat score due to equipment barriers"
        assert len(evidence["equipment_barriers"]) > 0
        assert "cryogenic" in evidence["equipment_barriers"] or "dilution refrigerator" in evidence["equipment_barriers"]
    
    def test_low_moat_with_open_source(self):
        """Test open source project has reduced moat score."""
        title = "Open Source Machine Learning Framework"
        abstract = "Code available on GitHub with reproducible results and public repository."
        keywords = ["open-source", "github"]
        
        score, evidence = calculate_moat_score(title, abstract, keywords)
        
        assert score < 0.7, "Open source should reduce moat score"
        assert len(evidence["openness_signals"]) > 0
    
    def test_compute_barriers(self):
        """Test detection of computational barriers."""
        title = "Large Scale Simulation"
        abstract = "Requires supercomputer with GPU cluster and petaflop performance for training."
        keywords = []
        
        score, evidence = calculate_moat_score(title, abstract, keywords)
        
        assert score > 0.3
        assert len(evidence["compute_barriers"]) > 0
    
    def test_material_barriers(self):
        """Test detection of material barriers."""
        title = "Rare Earth Element Applications"
        abstract = "Novel use of exotic materials and rare earth compounds."
        keywords = ["materials"]
        
        score, evidence = calculate_moat_score(title, abstract, keywords)
        
        assert score > 0.2
        assert len(evidence["material_barriers"]) > 0
    
    def test_no_barriers(self):
        """Test paper with no barriers has low moat score."""
        title = "Simple Algorithm for Data Processing"
        abstract = "A straightforward approach using standard techniques."
        keywords = ["algorithm"]
        
        score, evidence = calculate_moat_score(title, abstract, keywords)
        
        assert score < 0.3
        assert evidence["total_barriers"] == 0


class TestScalabilityScore:
    """Tests for scalability score calculation."""
    
    def test_high_scalability_cmos_compatible(self):
        """Test CMOS-compatible technology gets high scalability."""
        title = "CMOS Compatible Photonic Device"
        abstract = "Room temperature operation with standard fabrication at commercial foundry."
        keywords = ["cmos", "silicon"]
        
        score, evidence = calculate_scalability_score(title, abstract, keywords)
        
        assert score > 0.5, "CMOS compatible should have high scalability"
        assert len(evidence["manufacturing_signals"]) > 0
    
    def test_low_scalability_with_blockers(self):
        """Test technology with blockers gets low scalability."""
        title = "Cryogenic Quantum System"
        abstract = "Requires cryogenic conditions and manual calibration in cleanroom only environment."
        keywords = []
        
        score, evidence = calculate_scalability_score(title, abstract, keywords)
        
        assert score < 0.6, "Blockers should reduce scalability"
        assert len(evidence["blocker_signals"]) > 0
    
    def test_mature_technology(self):
        """Test mature technology signals increase scalability."""
        title = "Pilot Plant Demonstration"
        abstract = "TRL 7 demonstration with high yield production at pilot line showing cost effective manufacturing."
        keywords = ["pilot", "trl-7"]
        
        score, evidence = calculate_scalability_score(title, abstract, keywords)
        
        assert score > 0.4
        assert len(evidence["maturity_signals"]) > 0 or len(evidence["economic_signals"]) > 0
    
    def test_economic_signals(self):
        """Test economic signals boost scalability."""
        title = "Low Cost Manufacturing Process"
        abstract = "Economical and high yield batch processing for affordable mass production."
        keywords = []
        
        score, evidence = calculate_scalability_score(title, abstract, keywords)
        
        assert score > 0.4
        assert len(evidence["economic_signals"]) > 0
    
    def test_no_signals(self):
        """Test paper with no scalability signals has neutral score."""
        title = "Theoretical Framework"
        abstract = "Mathematical model and simulation results."
        keywords = ["theory"]
        
        score, evidence = calculate_scalability_score(title, abstract, keywords)
        
        assert 0.0 <= score <= 0.3
        assert evidence["positive_signals"] == 0


class TestZScoreNormalization:
    """Tests for z-score normalization."""
    
    def test_score_at_mean(self):
        """Test score at mean normalizes to 0.5."""
        score = normalize_score_zscore(0.5, domain_mean=0.5, domain_std=0.2)
        assert abs(score - 0.5) < 0.01
    
    def test_score_above_mean(self):
        """Test score above mean normalizes above 0.5."""
        score = normalize_score_zscore(0.8, domain_mean=0.5, domain_std=0.2)
        assert score > 0.5
    
    def test_score_below_mean(self):
        """Test score below mean normalizes below 0.5."""
        score = normalize_score_zscore(0.2, domain_mean=0.5, domain_std=0.2)
        assert score < 0.5
    
    def test_zero_std(self):
        """Test handling of zero standard deviation."""
        score = normalize_score_zscore(0.5, domain_mean=0.5, domain_std=0.0)
        assert score == 0.5
    
    def test_clipping(self):
        """Test extreme values are clipped."""
        # Very high score should clip to near 1.0
        score_high = normalize_score_zscore(10.0, domain_mean=0.5, domain_std=0.2, clip_std=3.0)
        assert 0.95 <= score_high <= 1.0
        
        # Very low score should clip to near 0.0
        score_low = normalize_score_zscore(-10.0, domain_mean=0.5, domain_std=0.2, clip_std=3.0)
        assert 0.0 <= score_low <= 0.05
    
    def test_output_range(self):
        """Test output is always in [0, 1] range."""
        test_cases = [
            (0.0, 0.5, 0.2),
            (1.0, 0.5, 0.2),
            (0.5, 0.5, 0.2),
            (0.3, 0.7, 0.1),
            (0.9, 0.3, 0.15),
        ]
        
        for raw_score, mean, std in test_cases:
            normalized = normalize_score_zscore(raw_score, mean, std)
            assert 0.0 <= normalized <= 1.0, f"Score {normalized} out of range for inputs ({raw_score}, {mean}, {std})"
