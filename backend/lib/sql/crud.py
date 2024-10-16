from typing import Tuple, Optional, Sequence, Union, Protocol, TypeAlias, List
from sqlalchemy import Result, select, and_
from sqlalchemy.orm import Session

from backend.lib.sql import schemas, models
from backend.lib.sql.utils import (
    check_if_record_exists_by_id,
    user_id_condition,
    student_name_condition,
    teacher_name_condition,
    create_option_model,
    create_question_model,
)
from backend.lib.sql.exceptions import (
    TemplateNotFoundException,
    QuestionnaireNotFound,
)


class ObjectHasTemplateID(Protocol):
    id: str


HasID: TypeAlias = Union[ObjectHasTemplateID, str]


def get_template_by_id(
    db: Session,
    template: HasID,
) -> Optional[models.QuestionTemplate]:
    """
    Retrieve a question template by its ID from the database.

    Args:
        db (Session): The database session to use for the query.
        template (schemas.QuestionTemplateBase): The template data
        containing the ID of the template to retrieve.

    Returns:
        Optional[models.QuestionTemplate]: The template if found, otherwise None.
    """
    with db.begin():
        if not isinstance(template, str):
            template = template.id

        result: Result[Tuple[models.QuestionTemplate]] = db.execute(
            statement=select(models.QuestionTemplate).where(
                models.QuestionTemplate.id == template
            )
        )
        return result.scalars().first()


def get_all_templates(
    db: Session,
) -> Sequence[models.QuestionTemplate]:
    """
    Retrieve all question templates from the database.

    Args:
        db (Session): The database session to use for the query.

    Returns:
        Sequence[models.QuestionTemplate]: A sequence, typically a
        list, of all question templates in the database. If no templates
        are found, an empty sequence is returned.
    """

    with db.begin():
        result: Result[Tuple[models.QuestionTemplate]] = db.execute(
            statement=select(models.QuestionTemplate)
        )
        return result.scalars().all()


def get_templates_by_title(
    db: Session, title: str
) -> Sequence[models.QuestionTemplate]:
    """
    Retrieve all question templates which contain the given title
    from the database.

    Args:
        db (Session): The database session to use for the query.
        title (str): The title of the templates to retrieve.

    Returns:
        Sequence[models.QuestionTemplate]: A sequence, typically a
        list, of all question templates with the given title. If no templates are found, an empty sequence is returned.
    """

    with db.begin():
        result: Result[Tuple[models.QuestionTemplate]] = db.execute(
            statement=select(models.QuestionTemplate).where(
                models.QuestionTemplate.title.like(other=f"%{title}%")
            )
        )
        return result.scalars().all()


def add_template(
    db: Session, template: schemas.CreateQuestionTemplateModel
) -> models.QuestionTemplate:
    """
    Adds a new question template to the database.

    Args:
        db (Session): The database session to use for the operation.
        template (schemas.QuestionTemplateCreate): The template data to be added.

    Returns:
        models.QuestionTemplate: The newly created question template instance.

    Raises:
        TemplateAlreadyExistsException: If a template with the given ID already exists.
    """
    with db.begin():
        # Create the new template
        new_template = models.QuestionTemplate(
            title=template.title,
            description=template.description,
        )

        # Create the new questions
        for question in template.questions:
            new_question: models.Question = create_question_model(
                schema=question,
                template_id=new_template.id,
            )
            new_template.questions.append(new_question)

        # Create the new options
        for index, question in enumerate(iterable=template.questions):
            for option in question.options:
                new_option: models.Option = create_option_model(
                    schema=option,
                    question_id=new_question.id,
                )
                new_template.questions[index].options.append(new_option)

        db.add(instance=new_template)
        return new_template


def update_template(
    db: Session,
    existing_id: HasID,
    updated_template: schemas.UpdateQuestionTemplateModel,
) -> models.QuestionTemplate:
    """
    Update an existing question template in the database.

    Args:
        db (Session): The database session.
        template (schemas.QuestionTemplateUpdate): The template data to update.

    Returns:
        models.QuestionTemplate: The updated question template.

    Raises:
        TemplateNotFoundException: If the template with the given ID does not exist.
    """
    if not isinstance(existing_id, str):
        existing_id = existing_id.id

    existing_template: Optional[models.QuestionTemplate] = get_template_by_id(
        db=db, id=existing_id
    )
    if not existing_template:
        raise TemplateNotFoundException(template_id=existing_id)

    try:
        # Update the base template data
        existing_template.title = updated_template.title
        existing_template.description = updated_template.description

        # Update the existing questions
        try:
            for existing_question, updated_question in zip(
                existing_template.questions, updated_template.questions, strict=True
            ):
                existing_question.title = updated_question.title
                existing_question.selected_option = updated_question.selected_option
                existing_question.custom_answer = updated_question.custom_answer

                # Update the existing options for the current question
                try:
                    for existing_option, updated_option in zip(
                        existing_question.options,
                        updated_question.options,
                        strict=True,
                    ):
                        existing_option.value = updated_option.value
                        existing_option.label = updated_option.label
                        existing_option.is_custom = updated_option.is_custom
                except ValueError:
                    if len(existing_question.options) > len(updated_question.options):
                        # Delete any extra options
                        for _ in range(
                            len(updated_question.options),
                            len(existing_question.options),
                        ):
                            db.delete(instance=existing_question.options.pop())
                    elif len(existing_question.options) < len(updated_question.options):
                        # Add any missing options
                        extra_options: int = len(existing_question.options)
                        for option in updated_question.options[extra_options:]:
                            new_option: models.Option = add_option(
                                db=db,
                                option=option,
                                question_id=existing_question.id,
                            )
                            existing_question.options.append(new_option)
                    else:
                        raise

        except ValueError:
            if len(existing_template.questions) > len(updated_template.questions):
                # Delete any extra questions
                for _ in range(
                    len(updated_template.questions),
                    len(existing_template.questions),
                ):
                    db.delete(instance=existing_template.questions.pop())
            elif len(existing_template.questions) < len(updated_template.questions):
                # Add any missing questions
                extra_questions: int = len(existing_template.questions)
                for question in updated_template.questions[extra_questions:]:
                    new_question: models.Question = add_question(
                        db=db,
                        question=question,
                        id=existing_template.id,
                    )
                    existing_template.questions.append(new_question)
            else:
                raise

    except Exception as e:
        db.rollback()
        raise e

    db.commit()
    return existing_template


def delete_template(db: Session, template: HasID) -> models.QuestionTemplate:
    """
    Deletes a question template from the database.

    This function deletes a question template identified by the given template data.
    It first flushes the current state of the database session, retrieves the template
    by its ID, and raises an exception if the template is not found. If the template
    exists, it is deleted from the database and the session is committed.

    Args:
        db (Session): The database session to use for the operation.
        template (schemas.QuestionTemplateBase): The template data containing the ID of the template to delete.

    Returns:
        models.QuestionTemplate: The deleted question template.

    Raises:
        TemplateNotFoundException: If the template with the given ID is not found.
    """

    template_to_delete: Optional[models.QuestionTemplate] = get_template_by_id(
        db=db, template=template
    )
    if not template_to_delete:
        if isinstance(template, str):
            raise TemplateNotFoundException(template_id=template)
        else:
            raise TemplateNotFoundException(template_id=template.id)

    db.delete(instance=template_to_delete)
    db.commit()
    return template_to_delete


def get_option_by_id(db: Session, option_id: int) -> Optional[schemas.OptionModel]:
    """
    Retrieve an option by its ID from the database.

    Args:
        db (Session): The database session to use for the query.
        option_id (int): The ID of the option to retrieve.

    Returns:
        Optional[schemas.OptionModel]: The option if found, otherwise None.
    """

    result: Result[Tuple[schemas.OptionModel]] = db.execute(
        statement=select(models.Option).where(models.Option.id == option_id)
    )
    return result.scalars().first()


def get_options_by_question_id(
    db: Session, question_id: int
) -> Sequence[schemas.OptionModel]:
    """
    Retrieve all options for a given question from the database.

    Args:
        db (Session): The database session to use for the query.
        question_id (int): The ID of the question to retrieve options for.

    Returns:
        Sequence[schemas.OptionModel]: A sequence, typically a list, of all options for the given question. If no options are found, an empty sequence is returned.
    """

    result: Result[Tuple[schemas.OptionModel]] = db.execute(
        statement=select(models.Option).where(models.Option.question_id == question_id)
    )
    return result.scalars().all()


def add_active_questionnaire(
    db: Session,
    questionnaire: schemas.ActiveQuestionnaireCreateModel,
) -> models.ActiveQuestionnaire:
    """
    Adds a new active questionnaire to the database. If the student or teacher
    associated with the questionnaire does not exist in the database, they are
    also added.

    Args:
        db (Session): The database session to use for the operation.
        questionnaire (schemas.ActiveQuestionnaireCreateModel): The questionnaire
            data to be added.

    Returns:
        models.ActiveQuestionnaire: The newly created active questionnaire record.
    """
    new_active_questionnaire = models.ActiveQuestionnaire(
        student_id=questionnaire.student.id,
        teacher_id=questionnaire.teacher.id,
        is_student_finished=False,
        is_teacher_finished=False,
        template_reference_id=questionnaire.id,
    )

    db.add(instance=new_active_questionnaire)

    # Check if the student exists in the database, if not add them
    if not check_if_record_exists_by_id(
        db=db, model=models.User, id=questionnaire.student.id
    ):
        new_student = models.User(
            id=questionnaire.student.id,
            user_name=questionnaire.student.user_name,
            full_name=questionnaire.student.full_name,
            role=questionnaire.student.role,
        )
        db.add(instance=new_student)

    # Check if the teacher exists in the database, if not add them
    if not check_if_record_exists_by_id(
        db=db, model=models.User, id=questionnaire.teacher.id
    ):
        new_teacher = models.User(
            id=questionnaire.teacher.id,
            user_name=questionnaire.teacher.user_name,
            full_name=questionnaire.teacher.full_name,
            role=questionnaire.teacher.role,
        )
        db.add(instance=new_teacher)

    db.commit()

    return new_active_questionnaire


def get_all_active_questionnaires(
    db: Session,
    teacher: str,
    student: str,
) -> Sequence[models.ActiveQuestionnaire]:
    """
    Retrieve all active questionnaires for a specific teacher and student.

    Args:
        db (Session): The database session to use for the query.
        teacher (str): The name of the teacher associated with the questionnaires.
        student (str): The name of the student associated with the questionnaires.

    Returns:
        Sequence[models.ActiveQuestionnaire]: A list of active questionnaires that match the given teacher and student.
    """

    result: Result[Tuple[models.ActiveQuestionnaire]] = db.execute(
        statement=select(models.ActiveQuestionnaire).where(
            and_(
                student_name_condition(student_name=student),
                teacher_name_condition(teacher_name=teacher),
            )
        )
    )
    return result.scalars().all()


def get_active_questionnaire_by_id(
    db: Session,
    questionnaire_id: str,
) -> Optional[models.ActiveQuestionnaire]:
    """
    Retrieve an active questionnaire by its ID from the database.

    Args:
        db (Session): The database session to use for the query.
        questionnaire_id (str): The ID of the questionnaire to retrieve.

    Returns:
        Optional[models.ActiveQuestionnaire]: The active questionnaire if found, otherwise None.
    """

    result: Result[Tuple[models.ActiveQuestionnaire]] = db.execute(
        statement=select(models.ActiveQuestionnaire).where(
            models.ActiveQuestionnaire.id == questionnaire_id
        )
    )
    return result.scalars().first()


def get_oldest_active_questionnaire_id_for_user(
    db: Session,
    user_id: str,
) -> Optional[str]:
    """
    Retrieve the ID of the oldest active questionnaire for a given user.

    Args:
        db (Session): The database session to use for the query.
        user_id (str): The ID of the user for whom to retrieve the oldest active questionnaire.

    Returns:
        Optional[str]: The ID of the oldest active questionnaire if found, otherwise None.
    """

    result: Result[Tuple[str]] = db.execute(
        statement=select(models.ActiveQuestionnaire.id)
        .where(user_id_condition(user_id=user_id))
        .order_by(models.ActiveQuestionnaire.created_at)
    )
    return result.scalars().first()


def get_all_active_questionnaire_ids_for_user(
    db: Session,
    user_id: str,
) -> Sequence[str]:
    """
    Retrieve all active questionnaire IDs for a given user.

    Args:
        db (Session): The database session to use for the query.
        user_id (str): The ID of the user for whom to retrieve active questionnaire IDs.

    Returns:
        Sequence[str]: A sequence of active questionnaire IDs for the specified user.
    """

    result: Result[Tuple[str]] = db.execute(
        statement=select(models.ActiveQuestionnaire.id)
        .where(user_id_condition(user_id=user_id))
        .order_by(models.ActiveQuestionnaire.created_at)
    )
    return result.scalars().all()


def delete_active_questionnaire(
    db: Session,
    questionnaire_id: str,
) -> models.ActiveQuestionnaire:
    """
    Deletes an active questionnaire from the database.

    Args:
        db (Session): The database session to use for the operation.
        questionnaire_id (str): The ID of the questionnaire to delete.

    Returns:
        models.ActiveQuestionnaire: The deleted active questionnaire object.

    Raises:
        QuestionnaireNotFound: If no active questionnaire is found with the given ID.
    """

    questionnaire_to_delete: Optional[models.ActiveQuestionnaire] = (
        get_active_questionnaire_by_id(db=db, questionnaire_id=questionnaire_id)
    )
    if not questionnaire_to_delete:
        raise QuestionnaireNotFound(questionnaire_id=questionnaire_id)

    db.delete(instance=questionnaire_to_delete)
    db.commit()
    return questionnaire_to_delete
