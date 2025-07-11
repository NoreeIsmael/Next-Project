using Logging.FileLogger;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Configuration;
using Settings.Default;

namespace Logging.Extensions;

public static class FileLoggerExtensions
{
    public static ILoggingBuilder AddFileLogger(
        this ILoggingBuilder builder)
    {
        builder.AddConfiguration();

        builder.Services.TryAddEnumerable(
            ServiceDescriptor.Singleton<ILoggerProvider, FileLoggerProvider>());

        LoggerProviderOptions.RegisterProviderOptions
            <DefaultFileLogger, FileLoggerProvider>(builder.Services);

        return builder;
    }

    public static ILoggingBuilder AddFileLogger(
        this ILoggingBuilder builder,
        Action<DefaultFileLogger> configure)
        {
            builder.AddFileLogger();
            builder.Services.Configure(configure);

            return builder;
        }
}
