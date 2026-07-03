from __future__ import annotations

from studyrag_core import PageText


COURSE_NAME = "StudyRAG Sample Course"
DOCUMENT_FILENAME = "study-rag-sample-course-notes.txt"


def sample_course_pages() -> list[PageText]:
    return [
        PageText(
            page_number=1,
            text=(
                "Related Rates\n"
                "Related rates problems connect quantities that change with time. "
                "Before differentiating, draw a diagram, label variables, and write an equation that connects the variables. "
                "Differentiate both sides of the equation with respect to time, using the chain rule for every quantity that changes. "
                "Substitute known values only after differentiating, then solve for the requested rate and include units.\n\n"
                "Related Rates Example\n"
                "For a ladder sliding down a wall, use x^2 + y^2 = L^2 where L is constant. "
                "Differentiating gives 2x dx/dt + 2y dy/dt = 0, so the horizontal and vertical rates are linked. "
                "A negative dy/dt means the top of the ladder is moving downward."
            ),
        ),
        PageText(
            page_number=2,
            text=(
                "Recursive Java Methods\n"
                "A recursive Java method solves a problem by calling itself on a smaller input. "
                "Every recursive method needs a base case that returns without making another recursive call. "
                "The recursive case must move the input toward the base case so the call chain eventually stops. "
                "Stack frames store each unfinished call, so deep recursion can cause a stack overflow.\n\n"
                "Factorial Recursion\n"
                "The factorial method can use if (n <= 1) return 1 as its base case. "
                "The recursive case returns n * factorial(n - 1), which reduces n by one on each call. "
                "For n = 4, the calls evaluate 4 * 3 * 2 * 1 after the base case returns."
            ),
        ),
        PageText(
            page_number=3,
            text=(
                "Newton's Method\n"
                "Newton's method approximates a root of f(x) by repeatedly applying x_next = x - f(x) / f'(x). "
                "The initial guess should be close enough to the desired root for the tangent-line approximation to be useful. "
                "Stop when the change between iterations is below a tolerance or when the function value is close to zero. "
                "If f'(x) is zero or nearly zero, the next step can be unstable.\n\n"
                "Newton's Method Interpretation\n"
                "Each Newton step uses the tangent line at the current estimate. "
                "The x-intercept of that tangent line becomes the next estimate. "
                "Fast convergence usually happens when the function is smooth and the starting estimate is reasonable."
            ),
        ),
        PageText(
            page_number=4,
            text=(
                "SQL Joins\n"
                "An inner join returns only rows where the join condition matches rows from both tables. "
                "A left join returns every row from the left table and fills unmatched right-table columns with NULL. "
                "Join conditions usually compare a primary key in one table to a foreign key in another table. "
                "Many-to-many relationships are represented with a bridge table that stores pairs of foreign keys.\n\n"
                "SQL Join Debugging\n"
                "Unexpected duplicate rows often mean the join condition is missing part of a composite key or the relationship is one-to-many. "
                "Unexpected missing rows often mean an inner join was used when a left join was needed. "
                "Filtering on a right-table column after a left join can accidentally remove NULL unmatched rows."
            ),
        ),
    ]
