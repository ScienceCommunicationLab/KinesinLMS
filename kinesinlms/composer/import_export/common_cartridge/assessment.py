from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from kinesinlms.assessments.models import Assessment
from kinesinlms.learning_library.constants import AssessmentType


@dataclass
class QTIChoice:
    identifier: str
    text: str


@dataclass
class QTIAssessment:
    identifier: str
    title: str
    max_score: int
    question_text: str
    explanation: Optional[str] = None

    @abstractmethod
    def to_qti_xml(self) -> str:
        """Convert the assessment to QTI XML string"""
        pass


class MultipleChoiceQTIAssessment(QTIAssessment):
    def __init__(
        self,
        identifier: str,
        title: str,
        max_score: int,
        question_text: str,
        choices: List[QTIChoice],
        correct_choice_keys: List[str],
        explanation: Optional[str] = None,
    ):
        super().__init__(identifier, title, max_score, question_text, explanation)
        self.choices = choices
        self.correct_choice_keys = correct_choice_keys

    def to_qti_xml(self) -> str:
        choices_xml = ""
        for choice in self.choices:
            choices_xml += f"""
                <response_label ident="{choice.identifier}">
                    <material>
                        <mattext texttype="text/plain">{choice.text}</mattext>
                    </material>
                </response_label>"""

        conditions_xml = ""
        for choice_key in self.correct_choice_keys:
            conditions_xml += f"""
            <respcondition continue="No">
                <conditionvar>
                    <varequal respident="response1">{choice_key}</varequal>
                </conditionvar>
                <setvar action="Set" varname="SCORE">{self.max_score}</setvar>
                <displayfeedback feedbacktype="Response" linkrefid="correct"/>
            </respcondition>"""

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<questestinterop xmlns="http://www.imsglobal.org/xsd/ims_qtiasiv1p2">
    <assessment ident="{self.identifier}" title="{self.title}">
        <qtimetadata>
            <qtimetadatafield>
                <fieldlabel>qmd_assessmenttype</fieldlabel>
                <fieldentry>Assessment</fieldentry>
            </qtimetadatafield>
        </qtimetadata>
        <section ident="root_section">
            <item ident="{self.identifier}_item1" title="{self.title}">
                <itemmetadata>
                    <qtimetadata>
                        <qtimetadatafield>
                            <fieldlabel>question_type</fieldlabel>
                            <fieldentry>multiple_choice_question</fieldentry>
                        </qtimetadatafield>
                        <qtimetadatafield>
                            <fieldlabel>points_possible</fieldlabel>
                            <fieldentry>{self.max_score}</fieldentry>
                        </qtimetadatafield>
                    </qtimetadata>
                </itemmetadata>
                <presentation>
                    <material>
                        <mattext texttype="text/html">{self.question_text}</mattext>
                    </material>
                    <response_lid ident="response1" rcardinality="Single">
                        <render_choice>
                            {choices_xml}
                        </render_choice>
                    </response_lid>
                </presentation>
                <resprocessing>
                    <outcomes>
                        <decvar maxvalue="100" minvalue="0" varname="SCORE" vartype="Decimal"/>
                    </outcomes>
                    {conditions_xml}
                </resprocessing>
            </item>
        </section>
    </assessment>
</questestinterop>"""


class TextEntryQTIAssessment(QTIAssessment):
    def to_qti_xml(self) -> str:
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<questestinterop xmlns="http://www.imsglobal.org/xsd/ims_qtiasiv1p2">
    <assessment ident="{self.identifier}" title="{self.title}">
        <qtimetadata>
            <qtimetadatafield>
                <fieldlabel>qmd_assessmenttype</fieldlabel>
                <fieldentry>Assessment</fieldentry>
            </qtimetadatafield>
        </qtimetadata>
        <section ident="root_section">
            <item ident="{self.identifier}_item1" title="{self.title}">
                <itemmetadata>
                    <qtimetadata>
                        <qtimetadatafield>
                            <fieldlabel>question_type</fieldlabel>
                            <fieldentry>text_entry_question</fieldentry>
                        </qtimetadatafield>
                        <qtimetadatafield>
                            <fieldlabel>points_possible</fieldlabel>
                            <fieldentry>{self.max_score}</fieldentry>
                        </qtimetadatafield>
                    </qtimetadata>
                </itemmetadata>
                <presentation>
                    <material>
                        <mattext texttype="text/html">{self.question_text}</mattext>
                    </material>
                    <response_str ident="response1" rcardinality="Single">
                        <render_fib>
                            <response_label ident="answer1"/>
                        </render_fib>
                    </response_str>
                </presentation>
                <resprocessing>
                    <outcomes>
                        <decvar maxvalue="100" minvalue="0" varname="SCORE" vartype="Decimal"/>
                    </outcomes>
                    <respcondition>
                        <conditionvar>
                            <other/>
                        </conditionvar>
                        <setvar varname="SCORE" action="Set">0</setvar>
                    </respcondition>
                </resprocessing>
            </item>
        </section>
    </assessment>
</questestinterop>"""


class QTIAssessmentFactory:
    """
    Factory for creating QTI assessment objects from our internal assessment models
    """

    def create_qti_assessment(self, assessment: Assessment) -> QTIAssessment:
        """
        Create appropriate QTI assessment based on assessment type

        Args:
            assessment: Assessment object

        Returns:
            QTIAssessment object
        """

        if assessment.type == AssessmentType.MULTIPLE_CHOICE.name:
            choices = []
            for choice in assessment.definition_json.get("choices", []):
                choices.append(QTIChoice(identifier=choice["choice_key"], text=choice["text"]))

            correct_choices = assessment.solution_json.get("correct_choice_keys", [])

            return MultipleChoiceQTIAssessment(
                identifier=str(assessment.id),
                title=assessment.label or "Untitled Assessment",
                max_score=assessment.max_score,
                question_text=assessment.question,
                choices=choices,
                correct_choice_keys=correct_choices,
                explanation=assessment.explanation,
            )

        elif assessment.type == AssessmentType.LONG_FORM_TEXT.name:
            return TextEntryQTIAssessment(
                identifier=str(assessment.id),
                title=assessment.label or "Untitled Assessment",
                max_score=assessment.max_score,
                question_text=assessment.question,
                explanation=assessment.explanation,
            )

        else:
            raise ValueError(f"Unsupported assessment type: {assessment.type}")
