using API.DTO.Responses.QuestionnaireTemplate;
using Database.Models;

namespace API.Extensions;

public static class QuestionnaireQuestionModelExtensions
{
    public static FetchQuestion ToDto(this QuestionnaireQuestionModel question)
    {
        return new FetchQuestion
        {
            Id = question.Id,
            Prompt = question.Prompt,
            AllowCustom = question.AllowCustom,
            Options = [.. question.Options.Select(o => o.ToDto())]
        };
    }
}
