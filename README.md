# Discord Scrim Manager Bot


A Discord bot for organizing and managing gaming scrimmages with automated randomized team creation and voice channel management.


## Commands

### Player Commands
 - `/create_scrim` - Creates a new scrim
 - `/join_scrim` - Joins an existing scrim
 - `/leave_scrim` - Leaves a scrim you've joined
 - `/list_scrims` - Displays all active scrims
 - `/scrim_info` - Displays detailed info about a specific scrim
 - `/my_scrims` - Displays your scrim history

### Admin Commands
 - `/start_scrim` - Starts a scrim (moves players to team channels)
 -  `/end_scrim` - Ends a scrim and cleans up team channels
 -  `/cancel_scrim` - Cancels a scrim and notifies players
 -  `/message_scrim` - Sends a custom message to all scrim participants
 -  `/purge_old_scrims` - Cleans up old completed scrims
