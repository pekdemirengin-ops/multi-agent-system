"""Skill-based agents."""
from agents.skills.translator_agent import TranslatorAgent
from agents.skills.calculator_agent import CalculatorAgent
from agents.skills.file_manager_agent import FileManagerAgent
from agents.skills.fact_checker_agent import FactCheckerAgent
from agents.skills.data_analyst_agent import DataAnalystAgent
from agents.skills.quiz_maker_agent import QuizMakerAgent
from agents.skills.email_composer_agent import EmailComposerAgent
from agents.skills.social_media_agent import SocialMediaAgent

__all__ = [
    "TranslatorAgent", "CalculatorAgent", "FileManagerAgent",
    "FactCheckerAgent", "DataAnalystAgent", "QuizMakerAgent",
    "EmailComposerAgent", "SocialMediaAgent",
]

from agents.skills.web_scraper_agent import WebScraperAgent

__all__ = __all__ + ["WebScraperAgent"]
