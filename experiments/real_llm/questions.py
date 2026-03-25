"""20 multi-hop questions in 4 categories for the real LLM experiment."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class Question:
    """A single evaluation question."""

    id: int
    text: str
    expected_tools: List[str]
    ground_truth_answer: str
    category: str


QUESTIONS: List[Question] = [
    # ---------------------------------------------------------------
    # Q1-Q5: Factual + Calculation (search_kb + calculator)
    # ---------------------------------------------------------------
    Question(
        id=1,
        text="What is the height of the Eiffel Tower in feet? First look up its height in meters, then convert.",
        expected_tools=["search_kb", "calculator"],
        ground_truth_answer="1082.68",
        category="factual_calculation",
    ),
    Question(
        id=2,
        text="How many times heavier is Earth than Mars? Look up both planets' diameters and calculate the ratio.",
        expected_tools=["search_kb", "calculator"],
        ground_truth_answer="1.88",  # 12742/6779
        category="factual_calculation",
    ),
    Question(
        id=3,
        text="If the Sun's diameter is about 109 times Earth's diameter, what is Earth's diameter? Look up the Sun's diameter and calculate.",
        expected_tools=["search_kb", "calculator"],
        ground_truth_answer="12778",  # 1392700/109
        category="factual_calculation",
    ),
    Question(
        id=4,
        text="How many human body lengths (average 1.7m) would it take to span the distance to the Moon? Look up the Moon's distance.",
        expected_tools=["search_kb", "calculator"],
        ground_truth_answer="226117647",  # 384400000/1.7
        category="factual_calculation",
    ),
    Question(
        id=5,
        text="What percentage of Bitcoin's max supply is 21 million? First look up Bitcoin's max supply, then calculate what percentage 1 million is of that.",
        expected_tools=["search_kb", "calculator"],
        ground_truth_answer="4.76",  # 1000000/21000000 * 100
        category="factual_calculation",
    ),

    # ---------------------------------------------------------------
    # Q6-Q10: Date/Time Reasoning (search_kb + date_math)
    # ---------------------------------------------------------------
    Question(
        id=6,
        text="The first modern Olympic Games were held in 1896. What day of the week was January 1, 1896?",
        expected_tools=["search_kb", "date_math"],
        ground_truth_answer="Wednesday",
        category="date_reasoning",
    ),
    Question(
        id=7,
        text="Python was first released in 1991. How many days between Python's first release (1991-02-20) and the Moon landing (1969-07-20)?",
        expected_tools=["search_kb", "date_math"],
        ground_truth_answer="7885",
        category="date_reasoning",
    ),
    Question(
        id=8,
        text="Bitcoin was created in 2009. What date is exactly 1000 days after January 3, 2009 (Bitcoin's genesis block)?",
        expected_tools=["search_kb", "date_math"],
        ground_truth_answer="2011-09-30",
        category="date_reasoning",
    ),
    Question(
        id=9,
        text="The Eiffel Tower was built in 1889. What day of the week was March 31, 1889 (its inauguration)?",
        expected_tools=["search_kb", "date_math"],
        ground_truth_answer="Sunday",
        category="date_reasoning",
    ),
    Question(
        id=10,
        text="Tim Berners-Lee invented the World Wide Web in 1989. How many days between the ARPANET (1969-10-29) and WWW invention (1989-03-12)?",
        expected_tools=["search_kb", "date_math"],
        ground_truth_answer="7104",
        category="date_reasoning",
    ),

    # ---------------------------------------------------------------
    # Q11-Q15: Unit Conversion (unit_converter + calculator)
    # ---------------------------------------------------------------
    Question(
        id=11,
        text="Convert the speed of sound in air (343 m/s) to km/h, then calculate how many km sound travels in 5 minutes.",
        expected_tools=["unit_converter", "calculator"],
        ground_truth_answer="102.9",  # 343 * 3.6 = 1234.8 km/h; 1234.8 * 5/60 = 102.9
        category="unit_conversion",
    ),
    Question(
        id=12,
        text="The Great Wall of China is 21,196 km long. Convert this to miles and then calculate how many days it would take to walk it at 30 miles per day.",
        expected_tools=["unit_converter", "calculator"],
        ground_truth_answer="439",  # 21196 * 0.621371 = 13168.7; 13168.7/30 = 438.96
        category="unit_conversion",
    ),
    Question(
        id=13,
        text="Human body temperature is 37 Celsius. Convert to Fahrenheit, then calculate how many degrees above water's boiling point (in Fahrenheit) that is.",
        expected_tools=["unit_converter", "calculator"],
        ground_truth_answer="-113.4",  # 37C = 98.6F; 100C = 212F; 98.6 - 212 = -113.4
        category="unit_conversion",
    ),
    Question(
        id=14,
        text="The Amazon River discharges 209,000 m^3/s. Convert the river's length (6,400 km) to meters and divide by the discharge rate to get seconds.",
        expected_tools=["search_kb", "unit_converter", "calculator"],
        ground_truth_answer="30.62",  # 6400000/209000 = 30.62
        category="unit_conversion",
    ),
    Question(
        id=15,
        text="A DNA double helix is 2 nm wide. Convert to meters, then calculate how many DNA strands side by side would span 1 millimeter (0.001 meters).",
        expected_tools=["search_kb", "unit_converter", "calculator"],
        ground_truth_answer="500000",  # 2nm = 2e-9m; 0.001/2e-9 = 500000
        category="unit_conversion",
    ),

    # ---------------------------------------------------------------
    # Q16-Q20: Multi-Step Verification (search_kb + calculator + verify_answer)
    # ---------------------------------------------------------------
    Question(
        id=16,
        text="Look up Mars' orbital period in days, then calculate how many Earth years that is (divide by 365.25). Verify your answer is approximately 1.88 years.",
        expected_tools=["search_kb", "calculator", "verify_answer"],
        ground_truth_answer="1.88",
        category="multi_step_verification",
    ),
    Question(
        id=17,
        text="Look up Mount Everest's height (8,849m) and the Eiffel Tower's height (330m). Calculate how many Eiffel Towers tall Everest is. Verify the answer is approximately 26.8.",
        expected_tools=["search_kb", "calculator", "verify_answer"],
        ground_truth_answer="26.81",
        category="multi_step_verification",
    ),
    Question(
        id=18,
        text="Look up the speed of light and calculate how long it takes light to travel from Earth to the Moon (384,400 km). Express in seconds. Verify approximately 1.28 seconds.",
        expected_tools=["search_kb", "calculator", "verify_answer"],
        ground_truth_answer="1.28",  # 384400000/299792458
        category="multi_step_verification",
    ),
    Question(
        id=19,
        text="Look up Tokyo's population and area. Calculate the population density (people per km^2). Verify it's approximately 6,361.",
        expected_tools=["search_kb", "calculator", "verify_answer"],
        ground_truth_answer="6361",  # 13960000/2194
        category="multi_step_verification",
    ),
    Question(
        id=20,
        text="Look up water's molar mass (18.015 g/mol) and density (1000 kg/m^3). Calculate how many moles of water are in 1 liter (1 kg = 1000g). Verify approximately 55.51 moles.",
        expected_tools=["search_kb", "calculator", "verify_answer"],
        ground_truth_answer="55.51",  # 1000/18.015
        category="multi_step_verification",
    ),
]
