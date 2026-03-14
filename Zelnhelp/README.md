# Vexus Helper Discord Bot

A comprehensive Discord bot for Vexus Helper with advanced moderation, utility, and payment features.

## 🚀 Features

### 🔧 Utility Commands
- **=whois <user>** - Shows detailed information about a user
- **=slotinfo <user>** - View Tier owner's slot info including expiry time and remaining pings
- **=si** - Displays server information and statistics
- **=find <product>** - Search for products (placeholder for future implementation)
- **=calc <expression>** - Perform mathematical calculations (Example: 10%8)
- **=convert <amount> <currency1> <currency2>** - Convert between currencies (Example: 10 usd eur)
- **=rm <time> [message]** - Set reminders (Example: rm 10m Check the channel)
- **=bal <address>** - Check Litecoin balance for an address
- **=tx <txID>** - View LTC Transaction details
- **=snipe** - View the last deleted message in the channel
- **=editsnipe** - View the last edited message in the channel
- **=invites** - Show your invite information
- **=ping** - Check bot latency and response time

### 🛡️ Mod Commands
- **=pm** - Sends the payment methods embed
- **=ltc <amount in USD>** - Generate LTC payment embed with QR code
- **=early [user]** - Give early supporter role to a user
- **=inv [user]** - Give merchant role to user
- **=purge <amount> [user]** - Delete messages (with optional user filter)
- **=echo <message>** - Echo a message
- **=notify [target] <msg>** - Send notification to a user in their DMs
- **=warn <user> <reason>** - Issue a warning to a user
- **=dewarn <user> <index>** - Remove a specific warning from a user
- **=warns [user]** - View all warnings for a user
- **=clearwarns <user>** - Remove all warnings from a user
- **=mute <user> <duration> [reason]** - Timeout a member
- **=unmute <user>** - Remove timeout

### 👑 Admin Commands
- **=role <user> <roleID/rolename>** - Assign or remove a role from a member
- **=cnuke** - Nuke the current channel
- **=apps <accept/hold/deny> <channelID(s)>** - Accept, deny, or hold staff applications
- **=restrict** - Set channel to members-only view
- **=private** - Set channel to member view, staff write
- **=full** - Set channel to staff-only access
- **=embed create** - Create a new embed using the embed builder
- **=embed edit <message_link>** - Edit an existing embed
- **=ban <user> [reason]** - Ban a user from the server
- **=kick <user> [reason]** - Kick a user from the server

### 🏷️ Tag System
- **=tagc <name> <content>** - Create a new tag
- **=tag <name>** - Use a tag
- **=taglist** - List all available tags
- **=tagdel <name>** - Delete a tag (admin only)

## 🎨 Styling & Branding

- **Brand**: Vexus Helper (updated from Zeldra)
- **Theme**: Orange color scheme (#FF8A00) instead of green
- **Embeds**: Modern Discord embeds with consistent styling
- **Help System**: Interactive help menu with select dropdowns
- **QR Codes**: Functional QR code generation for LTC payments

## 🔐 Permissions

### Mod Permissions
- Access to utility commands
- Basic moderation tools (warn, mute, purge)
- Payment and role management
- Tag system access

### Admin Permissions
- All mod permissions
- Channel management (restrict, private, full)
- User management (ban, kick)
- Application processing
- Embed creation and editing

## 🚀 Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure config.json**
   - Set your Discord bot token
   - Configure role IDs for admin and mod roles
   - Set up Blockcypher API token for crypto features
   - Customize branding and theme colors

3. **Run the Bot**
   ```bash
   python bot.py
   ```

## 🔧 Configuration

### Required Environment Variables
- `DISCORD_TOKEN` - Your Discord bot token

### Optional Configuration
- `BLOCKCYPHER_TOKEN` - Blockcypher API token for enhanced crypto features
- Custom role IDs for admin and mod permissions
- Custom branding and theme colors

## 🆕 Recent Updates

- ✅ Updated branding from "Zeldra" to "Vexus Helper"
- ✅ Changed theme from green to orange (#FF8A00)
- ✅ Replaced Blockchair API with Blockcypher API for better reliability
- ✅ Added comprehensive tag system
- ✅ Implemented new moderation commands (warn, purge, echo)
- ✅ Added channel management commands (restrict, private, full)
- ✅ Enhanced help system with new command categories
- ✅ Fixed LTC payment QR code generation
- ✅ Added reminder system
- ✅ Implemented warning system with persistence
- ✅ Added invite tracking
- ✅ Enhanced currency conversion

## 🐛 Bug Fixes

- Fixed critical API issues with Blockchair
- Resolved QR code generation problems
- Corrected permission system for new commands
- Fixed regex patterns in moderation commands
- Resolved embed styling inconsistencies

## 📝 Notes

- The bot now uses Blockcypher API instead of Blockchair for better reliability
- All embeds now use "Vexus Helper" branding consistently
- Orange theme (#FF8A00) is applied throughout the interface
- Tag system stores data locally in JSON format
- Warning system uses in-memory storage (consider database for production)

## 🤝 Contributing

Feel free to contribute to this project by:
- Reporting bugs
- Suggesting new features
- Submitting pull requests
- Improving documentation

## 📄 License

This project is proprietary to Vexus Helper.
