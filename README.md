# BetterBan Discord Bot

BetterBan is a Discord bot focused on improving the banning experience by providing additional features such as temp bans, sticky roles, and more. It's designed to provide server administrators with more control over their server's moderation.

## Features

- Temp bans: Ban users temporarily and automatically unban them after the specified duration.
- Sticky roles: Assign a role to a user that persists even if they leave and rejoin the server.
- Custom ban list: Ban users by their ID, even if they are not currently in the server.
- Ban management: View and remove warnings and bans.
- Logging: Set a custom logging channel for the bot's events.
- Error handling: Error IDs for easy reporting and resolution.
- And more...

## Installation

1. Click on the [invite link](https://discord.com/api/oauth2/authorize?client_id=975814318199287898&permissions=1101927573574&redirect_uri=https%3A%2F%2Fbban.raadsel.tech%2Finvited&scope=bot) to invite the bot to your server.
2. Grant the bot the necessary permissions.
3. Once the bot is in your server, set up the log channel using the `!set_log_channel` command followed by the channel mention where you want to log events. For example: `!set_log_channel #bot-log`
4. Use `/help` to see all the available commands.

## Commands

- `/help` - Shows a list of available commands and their descriptions.
- `/bban` - Bans a user from your guild, even if they aren't in your server!
- `/unbban` - Unbans a user if they were Bbanned.
- `/listbban` - Gets a list of all the bbanned users.
- `/tempban` - Temporarily bans a user.
- `/viewwarns` - View all the warnings of a user.
- `/removewarn` - Remove a warning from a user.
- `/set_sticky_role` - Set a sticky role for a user that persists even after they leave and rejoin the server.
- `/invite` - Get the invite link for the bot.
- `/leave` - [Bot owner only] Makes the bot leave the guild.
- `/warn` - Warn a user.
- `/info` - Get some info about the bot.
- `/set_log_channel` - Set the channel to log messages of the bot.
- `/remove_all_bban` - Removes all BBanned users.

## Support

If you encounter any issues or have any questions, please [open an issue](https://github.com/Raadsl/BetterBan/issues) on GitHub.