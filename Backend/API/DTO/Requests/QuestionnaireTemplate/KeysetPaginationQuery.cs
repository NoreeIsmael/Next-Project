using System.ComponentModel;
using API.Enums;

namespace API.DTO.Requests.QuestionnaireTemplate;

public record class KeysetPaginationQuery
{
    /// <summary>
    /// How many items the pagination query should return.
    /// </summary>
    [DefaultValue(5)]
    public required int PageSize { get; set; }
    
    /// <summary>
    /// The order in which the items should be paginated and queried in.
    /// </summary>
    [DefaultValue(QuestionnaireBaseTemplateOrdering.CreatedAtDesc)]
    public QuestionnaireBaseTemplateOrdering Order { get; set; } = QuestionnaireBaseTemplateOrdering.CreatedAtDesc;
    
    /// <summary>
    /// The title to search for in the templates.
    /// </summary>
    public string? Title { get; set; }

    /// <summary>
    /// The ID of the exact template. Partial search is not supported.
    /// </summary>
    public Guid? Id { get; set; }
    
    /// <summary>
    /// The cursor for where the query should start/resume from
    /// </summary>
    public string? QueryCursor { get; set; }
}
