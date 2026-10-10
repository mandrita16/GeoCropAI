def get_fertilizer_recommendation(fertilizer_name: str) -> str:
    """
    Format the fertilizer class predicted by the ML model.
    This function does not calculate application quantities.
    """

    fertilizer_info = {
        "Urea": (
            "Urea is a nitrogen fertilizer. Apply only when soil "
            "testing and crop requirements indicate a nitrogen need."
        ),
        "DAP": (
            "DAP (diammonium phosphate) supplies nitrogen and phosphorus. "
            "Use according to soil test results and crop requirements."
        ),
        "MOP": (
            "MOP (muriate of potash) supplies potassium. "
            "Confirm potassium requirements before application."
        ),
        "14-35-14": (
            "This is an NPK fertilizer grade. Check the product label "
            "and soil nutrient requirements before applying."
        ),
        "28-28": (
            "This label may refer to a blended fertilizer grade. "
            "Verify the exact product composition before use."
        ),
        "17-17-17": (
            "This is a balanced NPK fertilizer grade. "
            "Select application rates based on soil testing and crop needs."
        ),
        "20-20": (
            "Verify the complete fertilizer grade and product label "
            "before using this product."
        ),
        "10-26-26": (
            "This NPK fertilizer grade supplies nitrogen, phosphorus "
            "and potassium. Confirm the crop's nutrient requirements."
        ),
    }

    description = fertilizer_info.get(
        fertilizer_name,
        "Follow the product label and locally recommended application "
        "guidance for this fertilizer."
    )

    return f"{fertilizer_name}: {description}"
