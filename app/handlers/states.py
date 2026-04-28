"""
Conversation state constants.
Single source of truth — import these everywhere, never use raw strings.
"""

IDLE = "IDLE"
ONBOARDING_TZ = "ONBOARDING_TZ"
ONBOARDING_TIME = "ONBOARDING_TIME"
IN_CHECKIN_1 = "IN_CHECKIN_1"    # Waiting for challenge answer
IN_CHECKIN_2 = "IN_CHECKIN_2"    # Waiting for gratitude answer
IN_CHECKIN_3 = "IN_CHECKIN_3"    # Waiting for intention answer
AWAITING_LLM = "AWAITING_LLM"    # Submitted, waiting for LLM response
