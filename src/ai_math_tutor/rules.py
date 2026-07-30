EXTRACTION_RULES = r"""
convertt the image into thtis format: 
Line: latex format
Operation: operation the user performed win words
Line: next line in latex format
Operation: the next operation the user performed on this line in words
"""
        
REASONING_RULES = r"""
Use all of the context you have available to answer the students questtion in the most mathimatically accurate way. write it as a note to a math tutor not directly to the student. 
"""

TUTOR_RULES = r"""
Convert the reasoning note and into a tutor like response for helping the student with their question not just giving answers, word the tutoring response in a level approprate for the level of math. The response should be enttierly spoken words, inteded for speech. Do not use any latex format or symbols in this response at all. 
"""

