from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging

class SimilarityGuard:
    def __init__(self, threshold: float = 0.85):
        self.threshold = threshold
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.logger = logging.getLogger(__name__)

    def is_duplicate(self, new_question: str, existing_questions: list[str]) -> bool:
        if not existing_questions:
            return False
            
        try:
            # We add the new question to the end for calculation
            documents = existing_questions + [new_question]
            tfidf_matrix = self.vectorizer.fit_transform(documents)
            
            # Compute cosine similarity between new question and existing ones
            similarities = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1])[0]
            max_sim = max(similarities)
            
            self.logger.info(f"Max similarity found: {max_sim:.2f}")
            return bool(max_sim > self.threshold)
        except Exception as e:
            self.logger.error(f"Error computing similarity: {e}")
            # Safe fail - allow if we can't check
            return False
