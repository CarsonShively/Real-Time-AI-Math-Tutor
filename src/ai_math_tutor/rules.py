EXTRACTION_RULES = r"""
Convert what you see in the image to a document, one to one recreation of what was seen including new lines.
"""
        
REASONING_RULES = r"""
Use all of the context you have available to answer the students correctly. Write your answer as a note to a tutor not directly to the student, include 1 latex formated aid seperate from the note. Format the output in thte following JSON: {"note": "", "tutoring_aid": ""}
"""

TUTOR_RULES = r"""
Convert the reasoning note and tutoring aid into a tutor like response not just giving answers. The response should be enttierly spoken words, numbers spelled out as words etc, inteded for speech.
"""

