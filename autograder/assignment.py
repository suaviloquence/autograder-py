"""
What is necessary to grade a single assignment.
"""

import inspect

import autograder.code
import autograder.question
import autograder.utils

class Assignment(object):
    """
    A collection of questions to be scored.
    """

    def __init__(self,
            name = None,
            questions = [],
            submission_dir = '.', assignment_dir = '.',
            prep_submission = True,
            additional_data = {},
            **kwargs):
        """
        Construct an assignment.

        If prep_submission is True, then the default _prepare_submission()
        implementation will prepare the submission directory.
        """

        self._name = name
        if (self._name is None):
            self._name = type(self).__name__

        self._questions = questions

        self._assignment_dir = assignment_dir
        self._submission_dir = submission_dir
        self._prep_submission = prep_submission

        self._additional_data = additional_data

        # Scoring artifact.
        self.result = None

    def grade(self, **kwargs):
        return self._grade_submission(self._prepare_submission(), **kwargs)

    def _grade_submission(self, submission, show_exceptions = False, **kwargs):
        """
        Grade an assignment by grading all the questions.

        The submission argument is the result of _prepare_submission().
        """

        self.result = GradedAssignment(name = self._name, questions = [])
        self.result.grading_start_time = autograder.utils.get_timestamp()

        for question in self._questions:
            self.result.questions.append(question.grade(submission,
                additional_data = self._additional_data,
                show_exceptions = show_exceptions))

        self.result.grading_end_time = autograder.utils.get_timestamp()

        return self.result

    def _prepare_submission(self):
        """
        Prepare the submission directory for grading.
        The result of this is what will be passed to grade().
        Child classes may leave this default behavior or override.

        This implementation will check the prep_submission argument passed in the constructor.
        If true the submission directory will be prepared, otherwise None will be returned.
        """

        if (self._prep_submission):
            return autograder.utils.prepare_submission(self._submission_dir)

        return None

class GradedAssignment(object):
    """
    The result of an assignment being graded with a submission.
    """

    def __init__(self, name = '', questions = [],
            grading_start_time = None, grading_end_time = None,
            **kwargs):
        self.name = name
        self.questions = questions

        self.grading_start_time = None
        if (grading_start_time is not None):
            self.grading_start_time = autograder.utils.get_timestamp(grading_start_time)

        self.grading_end_time = None
        if (grading_end_time is not None):
            self.grading_end_time = autograder.utils.get_timestamp(grading_end_time)

    def to_dict(self):
        """
        Convert to all simple structures that can be later converted to JSON.
        """

        return {
            'name': self.name,
            'questions': [question.to_dict() for question in self.questions],
            'grading_start_time': autograder.utils.timestamp_to_string(self.grading_start_time),
            'grading_end_time': autograder.utils.timestamp_to_string(self.grading_end_time),
        }

    @staticmethod
    def from_dict(data):
        """
        Partner to to_dict().
        """

        data = dict(data)

        if ('questions' in data):
            data['questions'] = [autograder.question.GradedQuestion(**question) for question in data['questions']]

        return GradedAssignment(**data)

    def get_score(self):
        """
        Return (total score, max score).
        """

        total_score = 0
        max_score = 0

        for question in self.questions:
            total_score += question.score
            max_score += question.max_points

        return (total_score, max_score)

    def report(self, prefix = ''):
        """
        Return a string representation of the grading for this assignment.
        """

        if ((prefix != '') and (not prefix.endswith(' '))):
            prefix += ' '

        output = [
            prefix + "Autograder transcript for assignment: %s." % (self.name),
            prefix + "Grading started at %s and ended at %s." % (
                autograder.utils.timestamp_to_string(self.grading_start_time, pretty = True),
                autograder.utils.timestamp_to_string(self.grading_end_time, pretty = True))
        ]

        total_score = 0
        max_score = 0

        for question in self.questions:
            total_score += question.score
            max_score += question.max_points

            output.append(question.scoring_report(prefix = prefix))

        output.append('')
        output.append(prefix + "Total: %d / %d" % (total_score, max_score))

        return "\n".join(output)

    def __eq__(self, other):
        return self.equals(other)

    def equals(self, other, **kwargs):
        if (not isinstance(other, GradedAssignment)):
            return False

        if ((self.name != other.name) or (len(self.questions) != len(other.questions))):
            return False

        for i in range(len(self.questions)):
            if (not self.questions[i].equals(other.questions[i], **kwargs)):
                return False

        return True

def load_assignments(path):
    """
    Recursively load all the assignments in a path (file or dir).
    """

    module = autograder.code.sanitize_and_import_path(path)
    assignments = []

    for name in dir(module):
        obj = getattr(module, name)

        if (not inspect.isclass(obj)):
            continue

        if (obj == autograder.assignment.Assignment):
            continue

        if (issubclass(obj, (autograder.assignment.Assignment,))):
            assignments.append(obj)

    return assignments

def fetch_assignment(path):
    """
    Recursively fetch a single assignment from a path.
    If exactly one assignment is not found, then raise an error.
    """

    assignments = load_assignments(path)

    if (len(assignments) == 0):
        raise ValueError(("Assignment file (%s) does not contain any instances of" +
            " autograder.assignment.Assignment.") % (path))
    elif (len(assignments) > 1):
        # TODO(eriq): Add in assignment-class to disambiguate files with multiple assignments.
        raise ValueError(("Assignment file (%s) contains more than one (%d) instances of" +
            " autograder.assignment.Assignment.") % (path, len(assignments)))

    return assignments[0]