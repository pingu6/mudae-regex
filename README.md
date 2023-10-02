<h3 align="center">Mudae Regex</h3>
<div align="center">

  <a href="https://discord.gg/XjWcDVvuPt">
      <img src="https://discordapp.com/api/guilds/1050103286323216535/widget.png?style=banner2" alt="Discord Server"/>
  </a>

</div>

---

<p align="center">List splitter for mudae and more.
    <br>
</p>

## Invite

There are two public instance of mudae regex because of [discord 100 server limit for non verified bots](https://support.discord.com/hc/en-us/articles/360040720412-Bot-Verification-and-Data-Allowlisting)

- [Reze](https://discord.com/oauth2/authorize?client_id=1038889836813226045&scope=bot+applications.commands&permissions=274878286912) (currently in 98 server)
- [Bocchi](https://discord.com/oauth2/authorize?client_id=1073708855848079432&scope=bot+applications.commands&permissions=274878286912) (currently in 67 server)
  > **Note**
  > I can't host them 24/7 so they aren't always online but anyone can host their own mudae regex bot and anyone is welcome it host a public instance that run 24/7

## Todolist

- [x] Migrate from postgresql to sqlite for easier self hosting
- [x] Using raw sql instaed of prisam orm
- [ ] Adding new command that calculate kakera react vales base on number of keys, player premium, bost kakera
- [ ] Adding regex command for `$rl`
- [ ] Breack down each command into separate file for better readability and modularity

## Privacy policy

The bot exclusively stores the server ID and server-specific bot prefix, automatically removing this data from the database when the bot is removed from a server, but only if the bot was online.

## Self Hosting

### Requirements

- [python 3.11+](https://www.python.org/downloads/) (note: check "Add python 3.11 to PATH")
- [git](https://git-scm.com/downloads) (note: check "Run Git from the Windows Command Promptt")
- [postgresql](https://www.postgresql.org/download/)

### Steps

1. Creating a bot account https://discordpy.readthedocs.io/en/stable/discord.html#creating-a-bot-account

2. Enable all of the three"Privileged Gateway Intents" https://discordpy.readthedocs.io/en/stable/intents.html#privileged-intents

3. Open powershell anywhere and clone the repo

   ```bash
   git clone https://github.com/pingu6/mudae-regex.git
   ```

4. Go to the repo directory `mudae-regex` and install the requirements

   ```powershell
   cd mudae-regex & pip install -U -r requirements.txt
   ```

5. Rename `config_example.toml` to `config.toml` and fill it

   ```powershell
   ren config_example.toml config.toml & notepad config.toml
   ```

6. Run `main.py` file

   ```powershell
   py main.py
   ```

7. Run `[bot prefix]jsk sync` to sync all the slash and context menu commands
