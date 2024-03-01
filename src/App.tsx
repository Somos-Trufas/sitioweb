import "./App.css";

function App() {
  return (
    <>
      <div className="card">
        <div>
          <img
            src="/assets/logo.gif"
            className="logo"
            alt="Somos Trufas logo"
          />
        </div>
        <img
          src={"/assets/hashtag.png"}
          className="logo"
          alt="Somos Trufas logo"
        />
        <p>¡Sitio en construcción!</p>
        <p>Estamos trabajando para darte la mejor experiencia</p>
        <a href="https://discord.gg/trufas">
          <button
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "1rem 2rem",
              margin: "2rem",
            }}
          >
            <img
              width={64}
              src="/assets/discord.png"
              style={{ marginRight: "1rem" }}
            />{" "}
            Entra a nuestro Discord
          </button>
        </a>
      </div>
    </>
  );
}

export default App;
