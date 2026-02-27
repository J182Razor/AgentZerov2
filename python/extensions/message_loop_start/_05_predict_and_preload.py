"""
Predict and Preload Extension
Uses TaskPredictor to observe message patterns and suggest pre-loading.
Runs at the start of each message loop iteration.
"""
from python.helpers.extension import Extension
from agent import LoopData


class PredictAndPreload(Extension):
    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        try:
            from python.helpers.predictor import get_predictor
            agent = self.agent
            ctx_id = agent.context.id if hasattr(agent, 'context') else "default"
            predictor = get_predictor(ctx_id)

            # Observe the current user message
            last_user_msg = ""
            if loop_data and hasattr(loop_data, 'user_message') and loop_data.user_message:
                msg = loop_data.user_message
                last_user_msg = str(getattr(msg, 'message', msg) or '')

            if last_user_msg:
                predictor.observe(last_user_msg)

            # Store prediction in loop_data params for downstream use
            if loop_data:
                prediction = predictor.predict_next()
                loop_data.params_temporary["task_prediction"] = {
                    "category": prediction.likely_category,
                    "confidence": prediction.confidence,
                    "preloads": prediction.suggested_preloads,
                }
        except Exception:
            pass  # Never block the message loop
