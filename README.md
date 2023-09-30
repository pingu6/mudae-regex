<h3 align="center">Mudae Regex</h3>
<div align="center">

![Discord](https://discord.com/api/guilds/1050103286323216535/widget.png?style=banner2)

</div>

---

<p align="center">list splitter for mudae and more.
    <br>
</p>

### invite:

There are two public instance of mudae regex because of [discord 100 server limit for non verified bots](https://support.discord.com/hc/en-us/articles/360040720412-Bot-Verification-and-Data-Allowlisting)

- [Reze](https://discord.com/oauth2/authorize?client_id=1038889836813226045&scope=bot+applications.commands&permissions=274878286912) (currently in 98 server)
- [Bocchi](https://discord.com/oauth2/authorize?client_id=1073708855848079432&scope=bot+applications.commands&permissions=274878286912) (currently in 67 server)
  > **Note**
  > i can't host them 24/7 so they aren't always online but anyone can host their own mudae regex bot and anyone is welcome it host a public instance that run 24/7

### todolist:

- [ ] migrate from postgresql to sqlite for easier self hosting
- [ ] using raw sql instaed of prisam orm
- [ ] adding new command that calculate kakera react vales base on number of keys, player premium, bost kakera
- [ ] add regex command for `$rl`
- [ ] breack down each command into separate file for better readability and modularity

### privacy policy:

the only thing that the bot store is server id and the bot prefix for each server also it get removed from the database when the bot is removed from the server (only if the bot was online)

### self-hosting:

---

#### requirements:

- [python 3.11+](https://www.python.org/downloads/)
- [git](https://git-scm.com/downloads)
- [postgresql](https://www.postgresql.org/download/)

#### steps

1. creating a bot account https://discordpy.readthedocs.io/en/stable/discord.html#creating-a-bot-account

2. enable all of the three"Privileged Gateway Intents" https://discordpy.readthedocs.io/en/stable/intents.html#privileged-intents

3. clone the repo

```bash
git clone https://github.com/pingu6/mudae-regex.git
```

4. cd to `mudae-regex` and install the requirements

```powershell
 cd mudae-regex & pip install -U -r requirements.txt
```

5. rename `schema_example.prisma` to `schema.prisma` and add your postgresql url

> **_tip:_** https://neovim.io/ is the best for editing config files

```powershell
ren schema_example.prisma schema.prisma & notepad schema.prisma
```

6. run [`prisma db push`](https://prisma-client-py.readthedocs.io/en/stable/#generating-prisma-client-python)
7. rename `config_example.toml` to `config.toml` and

```powershell
ren config_example.toml config.toml & notepad config.toml
```

8. run `main.py` file

```powershell
py main.py
```

9. run `[bot prefix]jsk sync` to sync all slash and context menu commands
