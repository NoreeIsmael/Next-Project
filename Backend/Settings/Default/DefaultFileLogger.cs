using Microsoft.Extensions.Logging;
using Settings.Interfaces;

namespace Settings.Default;

public class DefaultFileLogger : IFileLoggerSettings
{
    public bool IsEnabled { get; set; } = true;
    public Dictionary<string, LogLevel> LogLevel { get; set; } = new Dictionary<string, LogLevel>
    {
        { "Default", Microsoft.Extensions.Logging.LogLevel.Warning },
        { "API", Microsoft.Extensions.Logging.LogLevel.Information },
        { "Database", Microsoft.Extensions.Logging.LogLevel.Information},
        { "Microsoft.EntityFrameworkCore.Migrations", Microsoft.Extensions.Logging.LogLevel.Information}
    };
    public string Path { get; set; } = "./app.log";
}
