"""
Gemini AI Service
Google Gemini 2.5 Flash integration for intelligent chat responses
With fallback to hardcoded responses
"""
import os
from typing import Dict, List, Optional
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# Try importing Gemini library
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("google-generativeai not installed, using fallback mode")


class GeminiService:
    """
    Google Gemini AI integration
    
    Uses Gemini Flash 2.0 for intelligent responses.
    Falls back to hardcoded responses if API unavailable.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = None
        self.is_available = False
        
        if GEMINI_AVAILABLE and self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-2.5-flash')
                self.is_available = True
                logger.info("Gemini AI service initialized with gemini-2.5-flash")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini: {e}")
    
    def chat(
        self, 
        message: str, 
        layouts: List[Dict] = None,
        boundary_metadata: Dict = None
    ) -> Dict[str, str]:
        """
        Generate chat response
        
        Args:
            message: User's question
            layouts: Current layout options
            boundary_metadata: Site boundary info
            
        Returns:
            Dict with 'message' and 'model' keys
        """
        if self.is_available and self.model:
            try:
                response = self._gemini_chat(message, layouts, boundary_metadata)
                return {"message": response, "model": "gemini-2.5-flash"}
            except Exception as e:
                logger.warning(f"Gemini API error: {e}, using fallback")
        
        # Fallback to hardcoded responses
        response = self._fallback_chat(message, layouts)
        return {"message": response, "model": "fallback"}
    
    def _gemini_chat(
        self, 
        message: str, 
        layouts: List[Dict] = None,
        metadata: Dict = None
    ) -> str:
        """Call Gemini API with context"""
        
        # Build context from layouts
        context = self._build_context(layouts, metadata)
        
        prompt = f"""You are an AI assistant for AIOptimize™, an industrial estate planning system.

CONTEXT:
{context}

USER QUESTION: {message}

Provide a helpful, concise response about the layout options or optimization process.
Focus on practical advice and explain trade-offs clearly.
Keep your response under 150 words.
"""
        
        response = self.model.generate_content(prompt)
        return response.text
    
    def _build_context(self, layouts: List[Dict], metadata: Dict) -> str:
        """Build context string from current data"""
        parts = []
        
        if metadata:
            parts.append(f"Site: {metadata.get('area', 0):.0f} m² area, {metadata.get('perimeter', 0):.0f}m perimeter")
        
        if layouts:
            parts.append(f"\nGenerated {len(layouts)} layout options:")
            for layout in layouts:
                metrics = layout.get('metrics', {})
                parts.append(
                    f"- {layout.get('name', 'Option')}: "
                    f"{metrics.get('total_plots', 0)} plots, "
                    f"{metrics.get('total_area', 0):.0f}m² total, "
                    f"fitness={metrics.get('fitness', 0):.2f}"
                )
        
        return "\n".join(parts) if parts else "No site analyzed yet."
    
    def _fallback_chat(self, message: str, layouts: List[Dict] = None) -> str:
        """
        Hardcoded fallback responses based on keyword matching
        Per MVP-24h.md specification
        """
        msg_lower = message.lower()
        
        # Category: Layout differences
        if any(word in msg_lower for word in ["difference", "compare", "between", "options"]):
            if layouts and len(layouts) >= 3:
                return (
                    f"The three layout options offer different trade-offs:\n\n"
                    f"💰 **{layouts[0].get('name', 'Option 1')}**: Maximizes sellable area with more plots. "
                    f"Best for high-density industrial use.\n\n"
                    f"⚖️ **{layouts[1].get('name', 'Option 2')}**: Balanced approach with medium plot sizes. "
                    f"Good mix of space efficiency and plot utility.\n\n"
                    f"🏢 **{layouts[2].get('name', 'Option 3')}**: Premium layout with fewer, larger plots. "
                    f"Ideal for tenants needing more space per unit."
                )
            return "Please generate layouts first to compare options."
        
        # Category: Best option recommendation
        if any(word in msg_lower for word in ["best", "recommend", "which", "should"]):
            if layouts:
                best = max(layouts, key=lambda x: x.get('metrics', {}).get('fitness', 0))
                return (
                    f"Based on the optimization analysis, I recommend **{best.get('name', 'Option 1')}** "
                    f"with a fitness score of {best.get('metrics', {}).get('fitness', 0):.2f}.\n\n"
                    f"This option offers {best.get('metrics', {}).get('total_plots', 0)} plots "
                    f"totaling {best.get('metrics', {}).get('total_area', 0):.0f}m² of sellable area.\n\n"
                    f"However, the 'best' choice depends on your priorities - "
                    f"maximum revenue, balanced development, or premium positioning."
                )
            return "Please generate layouts first to get a recommendation."
        
        # Category: Compliance/regulations
        if any(word in msg_lower for word in ["compliance", "regulation", "setback", "legal", "zone"]):
            return (
                "All generated layouts comply with the following requirements:\n\n"
                "✅ **50m boundary setback**: All plots maintain minimum distance from site edges\n"
                "✅ **Plot spacing**: Adequate spacing between plots for access roads\n"
                "✅ **Geometry validation**: All plots have valid rectangular shapes\n\n"
                "The genetic algorithm automatically enforces these constraints during optimization."
            )
        
        # Category: Metrics explanation
        if any(word in msg_lower for word in ["metric", "fitness", "score", "calculate"]):
            return (
                "The layout metrics are calculated as follows:\n\n"
                "📊 **Fitness Score** = (Profit × 0.5) + (Compliance × 0.3) + (Efficiency × 0.2)\n\n"
                "- **Profit**: Based on total sellable area (more area = higher profit)\n"
                "- **Compliance**: 1.0 if all setback rules met, lower if violated\n"
                "- **Efficiency**: Ratio of plots placed vs. target count\n\n"
                "Higher fitness scores indicate better overall layouts."
            )
        
        # Category: Algorithm explanation
        if any(word in msg_lower for word in ["algorithm", "genetic", "how", "work", "optimize"]):
            return (
                "AIOptimize uses a **Genetic Algorithm (GA)** for optimization:\n\n"
                "1️⃣ **Initialize**: Create 10 random layout candidates\n"
                "2️⃣ **Evaluate**: Calculate fitness for each layout\n"
                "3️⃣ **Select**: Keep top 3 performers (elitism)\n"
                "4️⃣ **Mutate**: Create variations of elite layouts\n"
                "5️⃣ **Repeat**: Run for 20 generations\n\n"
                "This produces diverse, optimized solutions that balance multiple objectives."
            )
        
        # Category: Export
        if any(word in msg_lower for word in ["export", "dxf", "cad", "download", "autocad"]):
            return (
                "You can export layouts in **DXF format** for use in CAD software:\n\n"
                "📥 **Single Layout**: Click the DXF button on any option card\n"
                "📦 **All Layouts**: Use 'Export All as ZIP' for all three options\n\n"
                "DXF files include:\n"
                "- Site boundary and setback zones\n"
                "- Plot geometries with labels\n"
                "- Area annotations\n"
                "- Professional layer organization\n\n"
                "Files work with AutoCAD, LibreCAD, and free online DXF viewers."
            )
        
        # Default response
        return (
            "I'm your AI assistant for industrial estate planning. I can help you understand:\n\n"
            "• **Layout options** - Compare the three generated designs\n"
            "• **Optimization** - How the genetic algorithm works\n"
            "• **Metrics** - What fitness scores mean\n"
            "• **Compliance** - Setback and zoning rules\n"
            "• **Export** - Download DXF files for CAD software\n\n"
            "What would you like to know?"
        )


# Global instance
gemini_service = GeminiService()
