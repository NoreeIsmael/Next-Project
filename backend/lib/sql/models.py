from sqlalchemy import (
    Boolean,
    ExecutionContext,
    Exists,
    ForeignKey,
    Integer,
    String,
    DateTime,
    func,
    exists,
    select,
    event,
    Connection,
    MetaData,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    relationship,
    mapped_column,
    Mapped,
    Session,
    Mapper,
)
from sqlalchemy.orm.exc import NoResultFound
from datetime import datetime
from typing import List, Optional, LiteralString, Type
from random import choice
from string import ascii_letters, digits

from backend.lib.sql import db_logger

URL_FRIENDLY_BASE64: LiteralString = ascii_letters + digits + "-_"


def sql_func_generate_id(context: ExecutionContext) -> str:
    """
    Generates a unique random string ID for a SQL database entry.

    This function attempts to generate a unique 10-character random string
    using URL-friendly base64 characters. It checks the generated string
    against the `QuestionTemplate` table to ensure uniqueness. If a unique
    string is not generated within 5 attempts, it logs an error and raises
    a `ValueError`.

    Args:
        context (ExecutionContext): The SQLAlchemy execution context containing
                                    the database engine.

    Returns:
        str: A unique 10-character random string.

    Raises:
        ValueError: If a unique random string cannot be generated after 5 attempts.
    """
    attempts: int = 0
    with context.engine.begin() as connection:
        while True:
            random_string: str = "".join(
                choice(seq=URL_FRIENDLY_BASE64) for _ in range(10)
            )
            exists_criteria: Exists = exists().where(
                QuestionTemplate.id == random_string
            )
            result: Optional[bool] = connection.execute(
                statement=select(exists_criteria)
            ).scalar()
            if result is False:
                return random_string
            else:
                if attempts >= 5:
                    msg = "Failed to generate a unique random string after 5 attempts"
                    db_logger.error(msg=msg)
                    raise ValueError(msg)
                attempts += 1
                continue


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_`%(constraint_name)s`",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class Option(Base):
    """
    Represents an option for a question in the database.

    Attributes:
        id (int): The primary key of the option. Auto-incremented.
        question_id (int): The foreign key linking to the associated
            question.
        value (int): The value of the option. Can be used as a local
            index scoped to the question. I.e., if the answer has
            `selected_option_value` set to 2, it corresponds to the
            option with `value` set to 2.
        label (str): The label, title, or text of the option. This is
            what the user sees when selecting an option.
        is_custom (bool): Indicates if the option is custom or predefined.
            Defaults to False. Has no effect on the internal logic, but
            can be used to differentiate between custom and predefined
            options in the UI.

    Relationships:
        question (Question): The relationship to the associated question.

    Note:
        Relationships are automatically handled by SQLAlchemy. Once the
        ForeignKey `question_id` is set, the relationship is automatically
        established between the `Option` and `Question` models.
    """

    __tablename__: str = "options"

    id: Mapped[int] = mapped_column(type_=Integer, primary_key=True, index=True)
    question_id: Mapped[int] = mapped_column(
        type_=Integer, __type_pos=ForeignKey(column="questions.id")
    )
    value: Mapped[int] = mapped_column(type_=Integer, index=True)
    label: Mapped[str] = mapped_column(type_=String, index=True)
    is_custom: Mapped[bool] = mapped_column(type_=Boolean, index=False, default=False)

    question: Mapped["Question"] = relationship(back_populates="options")


class Question(Base):
    """
    Represents a question in the database.

    Attributes:
        id (Mapped[int]): The primary key of the question. Auto-incremented.
        template_id: (Mapped[str]): The foreign key referencing the question
            template with which the question is associated.
        title (Mapped[str]): The title of the question. This is the question
            which the user sees.

    Relationships:
        template (Mapped["QuestionTemplate"]): The relationship to the
            QuestionTemplate model.
        options (Mapped[List["Option"]]): The relationship to the
            Option model, with cascading delete-orphan.


    Note:
        Relationships are automatically handled by SQLAlchemy. Once the
        ForeignKey `template_id` is set, the relationship is automatically
        established between the `Question` and `QuestionTemplate` models.
    """

    __tablename__: str = "questions"

    id: Mapped[int] = mapped_column(type_=Integer, primary_key=True, index=True)
    template_id: Mapped[str] = mapped_column(
        type_=String, __type_pos=ForeignKey(column="question_templates.id")
    )
    title: Mapped[str] = mapped_column(type_=String, index=True)

    template: Mapped["QuestionTemplate"] = relationship(
        argument="QuestionTemplate", back_populates="questions"
    )
    options: Mapped[List["Option"]] = relationship(
        argument="Option", back_populates="question", cascade="all, delete-orphan"
    )


class QuestionTemplate(Base):
    """
    Represents a template for questions in the database.

    Attributes:
        id (Mapped[str]): The unique identifier for the question
            template, generated by `sql_func_generate_id`.
        title (Mapped[str]): The title of the question template.
        description (Mapped[str]): The description of the question template.
        created_at (Mapped[datetime]): The timestamp when the question
            template was created. Automatically set to the current time.
        last_updated (Mapped[datetime]): The timestamp when the question
            template was last updated. Automatically runs on row update.

    Relationships:
        questions (Mapped[List["Question"]]): The list of questions
            associated with this template.
        template_questionnaires (Mapped[List["ActiveQuestionnaire"]]):
            The list of active questionnaires associated with this template.

    Note:
        Relationships are automatically handled by SQLAlchemy. Once the
        ForeignKey `template_id` is set, the relationship is automatically
        established between the `Question` and `QuestionTemplate` models.
    """

    __tablename__: str = "question_templates"

    id: Mapped[str] = mapped_column(
        type_=String, primary_key=True, index=True, default=sql_func_generate_id
    )
    title: Mapped[str] = mapped_column(type_=String, index=True)
    description: Mapped[str] = mapped_column(type_=String, index=False)
    created_at: Mapped[datetime] = mapped_column(
        type_=DateTime(timezone=True), index=False, server_default=func.now()
    )
    last_updated: Mapped[datetime] = mapped_column(
        type_=DateTime(timezone=True),
        index=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    questions: Mapped[List["Question"]] = relationship(
        argument="Question", back_populates="template", cascade="all, delete-orphan"
    )
    template_questionnaires: Mapped[List["ActiveQuestionnaire"]] = relationship(
        argument="ActiveQuestionnaire", back_populates="template"
    )


class User(Base):
    """
    Represents a user in the system.

    Attributes:
        id (Mapped[str]): The primary key of the user, indexed. A hashed
            version of their Active Directory UUID
        user_name (Mapped[str]): The username of the user, indexed.
        full_name (Mapped[str]): The full name of the user.
        role (Mapped[str]): The role of the user.

    Relationships:
        student_questionnaires (Mapped[list["ActiveQuestionnaire"]]):
            The list of questionnaires associated with the user as a student.
        teacher_questionnaires (Mapped[list["ActiveQuestionnaire"]]):
            The list of questionnaires associated with the user as a teacher.

    Note:
        Relationships are automatically handled by SQLAlchemy. Once the
        ForeignKey `student_id` or `teacher_id` is set, the relationship is
        automatically established between the `User` and `ActiveQuestionnaire`
    """

    __tablename__: str = "users"

    id: Mapped[str] = mapped_column(type_=String, primary_key=True, index=True)
    user_name: Mapped[str] = mapped_column(type_=String, index=True)
    full_name: Mapped[str] = mapped_column(type_=String, index=False)
    role: Mapped[str] = mapped_column(type_=String, index=False)

    student_questionnaires: Mapped[list["ActiveQuestionnaire"]] = relationship(
        argument="ActiveQuestionnaire",
        foreign_keys="[ActiveQuestionnaire.student_id]",
        back_populates="student",
    )
    teacher_questionnaires: Mapped[list["ActiveQuestionnaire"]] = relationship(
        argument="ActiveQuestionnaire",
        foreign_keys="[ActiveQuestionnaire.teacher_id]",
        back_populates="teacher",
    )


class ActiveQuestionnaire(Base):
    """
    ActiveQuestionnaire model represents the active questionnaires assigned to students and teachers.

    Attributes:
        id (Mapped[str]): The primary key of the active questionnaire, generated by `sql_func_generate_id`.
        student_id (Mapped[str]): Foreign key referencing the `id` column in the `users` table.
        teacher_id (Mapped[str]): Foreign key referencing the `id` column in the `users` table.
        is_student_finished (Mapped[bool]): Indicates if the student has finished the questionnaire.
        is_teacher_finished (Mapped[bool]): Indicates if the teacher has finished the questionnaire.
        template_reference_id (Mapped[str]): Foreign key referencing the `id` column in the `question_templates` table.
        created_at (Mapped[datetime]): The timestamp when the active questionnaire was created, with timezone support.

    Relationships:
        student (Mapped["User"]): Relationship to the `User` model for the student.
        teacher (Mapped["User"]): Relationship to the `User` model for the teacher.
        template (Mapped["QuestionTemplate"]): Relationship to the `QuestionTemplate` model.
    """

    __tablename__: str = "active_questionnaires"

    id: Mapped[str] = mapped_column(
        type_=String, primary_key=True, index=True, default=sql_func_generate_id
    )
    student_id: Mapped[str] = mapped_column(
        type_=String, __type_pos=ForeignKey(column="users.id")
    )
    teacher_id: Mapped[str] = mapped_column(
        type_=String, __type_pos=ForeignKey(column="users.id")
    )
    is_student_finished: Mapped[bool] = mapped_column(type_=Boolean, index=False)
    is_teacher_finished: Mapped[bool] = mapped_column(type_=Boolean, index=False)
    template_reference_id: Mapped[str] = mapped_column(
        type_=String, __type_pos=ForeignKey(column="question_templates.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        type_=DateTime(timezone=True), index=False, server_default=func.now()
    )

    student: Mapped["User"] = relationship(
        argument="User",
        foreign_keys=[student_id],
        back_populates="student_questionnaires",
    )
    teacher: Mapped["User"] = relationship(
        argument="User",
        foreign_keys=[teacher_id],
        back_populates="teacher_questionnaires",
    )
    template: Mapped["QuestionTemplate"] = relationship(
        argument="QuestionTemplate",
        foreign_keys=[template_reference_id],
        back_populates="template_questionnaires",
    )


@event.listens_for(target=ActiveQuestionnaire, identifier="after_delete")
def delete_user_if_no_questionnaires(
    mapper: Mapper, connection: Connection, target: Type[ActiveQuestionnaire]
) -> None:
    """
    Event listener to delete a user if they have no remaining questionnaires.

    Args:
        mapper: The mapper.
        connection: The database connection.
        target: The instance of ActiveQuestionnaire being deleted.
    """
    session = Session(bind=connection)

    try:
        # Check if the student has any remaining questionnaires
        student_questionnaires = (
            session.query(ActiveQuestionnaire)
            .filter_by(student_id=target.student_id)
            .count()
        )
        if student_questionnaires == 0:
            student = session.query(User).filter_by(id=target.student_id).one()
            session.delete(student)

        # Check if the teacher has any remaining questionnaires
        teacher_questionnaires = (
            session.query(ActiveQuestionnaire)
            .filter_by(teacher_id=target.teacher_id)
            .count()
        )
        if teacher_questionnaires == 0:
            teacher = session.query(User).filter_by(id=target.teacher_id).one()
            session.delete(teacher)

        session.commit()
    except NoResultFound:
        pass
    finally:
        session.close()
