EXTRACTION_RULES = r"""
convertt the image into thtis format: 
Line: latex format
Operation: operation the user performed win words
Line: next line in latex format
Operation: the next operation the user performed on this line in words
"""
        
REASONING_RULES = r"""
Use all of the context you have available to answer the students questtion correctly. Write your answer as a note to the tutor not directly to the student. Use words only, Do nott use latex format or symbols at all.
"""

TUTOR_RULES = r"""
Convert the reasoning note and into a tutor like response for helping the student with their question not just giving answers. The response should be enttierly spoken words, inteded for speech. Do not use any latex format or symbols in this response at all. 
"""

