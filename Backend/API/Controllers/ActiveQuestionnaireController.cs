using System.IdentityModel.Tokens.Jwt;
using API.DTO.Requests.ActiveQuestionnaire;
using API.DTO.Responses.ActiveQuestionnaire;
using API.Exceptions;
using API.Services;
using Database.DTO.ActiveQuestionnaire;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace API.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class ActiveQuestionnaireController : ControllerBase
    {
        private readonly ActiveQuestionnaireService _questionnaireService;
        private readonly ILogger _logger;

        public ActiveQuestionnaireController(ActiveQuestionnaireService questionnaireService, ILoggerFactory loggerFactory)
        {
            _questionnaireService = questionnaireService;
            _logger = loggerFactory.CreateLogger(GetType());
        }

        [HttpGet]
        [Authorize(AuthenticationSchemes = "AccessToken")]
        public async Task<ActionResult<ActiveQuestionnaireKeysetPaginationResultAdmin>> GetActiveQuestionnaires([FromQuery] ActiveQuestionnaireKeysetPaginationRequestFull request)
        {
            return Ok(await _questionnaireService.FetchActiveQuestionnaireBases(request));
        }

        [HttpPost("activate")]
        [Authorize(AuthenticationSchemes = "AccessToken", Policy = "AdminOnly")]
        public async Task<ActionResult<ActiveQuestionnaire>> ActivateQuestionnaire([FromForm] ActivateQuestionnaire request)
        {
            return Ok(await _questionnaireService.ActivateTemplate(request));
        }

        [HttpGet("check")]
        [Authorize(AuthenticationSchemes = "AccessToken", Policy = "StudentAndTeacherOnly")]
        [ProducesResponseType(StatusCodes.Status204NoContent)]
        [ProducesResponseType(typeof(Guid), StatusCodes.Status200OK)]
        public async Task<ActionResult<Guid?>> CheckIfUserHasActiveQuestionnaire()
        {
            Guid userId;
            try
            {
                userId = Guid.Parse(User.Claims.First(x => x.Type == JwtRegisteredClaimNames.Sub).Value);
            }
            catch (Exception e)
            {
                _logger.LogError(e, "Error parsing user ID from claims: {Message}", e.Message);
                return Unauthorized();   
            }
            
            return await _questionnaireService.GetOldestActiveQuestionnaireForUser(userId);
        }

        [HttpGet("{id}")]
        [Authorize(AuthenticationSchemes = "AccessToken")]
        public async Task<ActionResult<ActiveQuestionnaire>> GetActiveQuestionnaire(Guid id)
        {
            return Ok(await _questionnaireService.FetchActiveQuestionnaire(id));
        }
        
        [HttpPut("{id}/submitAnswer")]
        [Authorize(AuthenticationSchemes = "AccessToken", Policy = "StudentAndTeacherOnly")]
        public async Task<ActionResult> SubmitQuestionnaireAnswer(Guid id, [FromBody] AnswerSubmission submission)
        {
            Guid userId;
            try
            {
                userId = Guid.Parse(User.Claims.First(x => x.Type == JwtRegisteredClaimNames.Sub).Value);
            }
            catch (Exception e)
            {
                _logger.LogError(e, "Error parsing user ID from claims: {Message}", e.Message);
                return Unauthorized();   
            }

            try
            {
                await _questionnaireService.SubmitAnswers(id, userId, submission);
            }
            catch(HttpResponseException ex)
            {
                _logger.LogError(ex, "Error submitting questionnaire answer: {Message}", ex.Message);
                return StatusCode((int)ex.StatusCode, ex.Message);
            }

            return Ok();
        }

        [HttpGet("{id}/getResponse")]
        [Authorize(AuthenticationSchemes = "AccessToken", Policy = "TeacherOnly")]
        public async Task<ActionResult<List<FullResponse>>> GetActiveQuestionnaireResponses(Guid id)
        {
            Guid userId;
            try
            {
                userId = Guid.Parse(User.Claims.First(x => x.Type == JwtRegisteredClaimNames.Sub).Value);
            }
            catch (Exception e)
            {
                _logger.LogError(e, "Error parsing user ID from claims: {Message}", e.Message);
                return Unauthorized();   
            }

            FullResponse response = await _questionnaireService.GetFullResponseAsync(id);

            if (userId != response.Student.User.Guid && userId != response.Teacher.User.Guid)
            {
                _logger.LogWarning("User {UserId} is not authorized to view questionnaire response for {QuestionnaireId}", userId, id);
                return Unauthorized();
            }
            else
            {
                return Ok(await _questionnaireService.GetFullResponseAsync(id));
            }
        }

        [HttpGet("{id}/isAnswered")]
        [Authorize(AuthenticationSchemes = "AccessToken", Policy = "StudentAndTeacherOnly")]
        public async Task<ActionResult<bool>> CheckIfQuestionnaireAnswered(Guid id)
        {
            Guid userId;
            try
            {
                userId = Guid.Parse(User.Claims.First(x => x.Type == JwtRegisteredClaimNames.Sub).Value);
            }
            catch (Exception e)
            {
                _logger.LogError(e, "Error parsing user ID from claims: {Message}", e.Message);
                return Unauthorized();   
            }

            return await _questionnaireService.HasUserSubmittedAnswer(userId, id);
        }

        [HttpGet("{id}/IsCompleted")]
        [Authorize(AuthenticationSchemes = "AccessToken", Policy = "TeacherOnly")]
        public async Task<ActionResult<bool>> CheckifQuestionnaireCompleted(Guid id)
        {
            Guid userId;
            try
            {
                userId = Guid.Parse(User.Claims.First(x => x.Type == JwtRegisteredClaimNames.Sub).Value);
            }
            catch (Exception e)
            {
                _logger.LogError(e, "Error parsing user ID from claims: {Message}", e.Message);
                return Unauthorized();   
            }

            return await _questionnaireService.IsActiveQuestionnaireComplete(id, userId);
        }
    }
}
