

import React, { useEffect, useState } from "react";

import {

  Routes,

  Route,

  Link,

  NavLink,

  useNavigate,

  useLocation,

} from "react-router-dom";



import {

  Leaf,

  Store,

  BrainCircuit,

  FlaskConical,

  ScanSearch,

  LogIn,

  LogOut,

  MapPin,

  CloudSun,

  UploadCloud,

  Sparkles,

  ShoppingCart,

  PackagePlus,

  Eye,

  EyeOff,

  ArrowUpRight,

  Sprout,

  ShieldCheck,

} from "lucide-react";



import { api } from "./api";



function user() {

  try {

    return JSON.parse(localStorage.getItem("user"));

  } catch {

    return null;

  }

}



/* =========================

   MAIN LAYOUT AND ROUTES

========================= */



function Layout() {

  const [u, setU] = useState(user());

  const nav = useNavigate();



  function out() {

    localStorage.removeItem("token");

    localStorage.removeItem("user");

    setU(null);

    nav("/");

  }



  return (

    <>

      <header>

        <div className="wrap nav">

          <Link className="brand" to="/">

            <i><Leaf size={19} /></i>

            Geo<span>Crop</span>AI

          </Link>



          <nav>

            <NavLink to="/" end>Home</NavLink>

            <NavLink to="/ai-tools">AI Tools</NavLink>

            <NavLink to="/marketplace">

              <Store size={15} /> Marketplace

            </NavLink>

            {u && <NavLink to="/dashboard">Dashboard</NavLink>}

          </nav>



          <div className="actions">

            {u ? (

              <>

                <span className="user">

                  {u.username} · {u.role}

                </span>

                <button

                  className="ghost"

                  onClick={out}

                  aria-label="Log out"

                  title="Log out"

                >

                  <LogOut size={15} />

                </button>

              </>

            ) : (

              <>

                <Link className="ghost" to="/login">

                  <LogIn size={15} /> Login

                </Link>

                <Link className="btn small" to="/signup">

                  Get started

                </Link>

              </>

            )}

          </div>

        </div>

      </header>



      <main>

        <Routes>

          <Route path="/" element={<Home />} />

          <Route path="/ai-tools" element={<AITools />} />



          <Route path="/login" element={<Login setU={setU} />} />

          <Route path="/signup" element={<Signup setU={setU} />} />



          <Route

            path="/dashboard"

            element={<Guard><Dashboard /></Guard>}

          />



          <Route

            path="/crop"

            element={<Guard><Crop /></Guard>}

          />



          <Route

            path="/fertilizer"

            element={<Guard><Fertilizer /></Guard>}

          />



          <Route

            path="/disease"

            element={<Guard><Disease /></Guard>}

          />



          <Route path="/marketplace" element={<Market />} />



          <Route

            path="/sell"

            element={<Guard role="farmer"><Sell /></Guard>}

          />



          <Route

            path="/listings"

            element={<Guard role="farmer"><Listings /></Guard>}

          />



          <Route

            path="/orders"

            element={<Guard><Orders /></Guard>}

          />



          <Route path="*" element={<NotFound />} />

        </Routes>

      </main>



      <footer>

        <div className="wrap">

          🌱 GeoCropAI · AI agriculture · Marketplace

        </div>

      </footer>

    </>

  );

}



/* =========================

   AUTHENTICATION GUARDS

========================= */



function Guard({ children, role }) {

  const u = user();

  const loc = useLocation();



  if (!u) {

    return <LoginRedirect from={loc.pathname} />;

  }



  if (role && u.role !== role) {

    return <NavigateHome />;

  }



  return children;

}



function LoginRedirect() {

  const nav = useNavigate();



  useEffect(() => {

    nav("/login");

  }, [nav]);



  return <Loader />;

}



function NavigateHome() {

  const nav = useNavigate();



  useEffect(() => {

    nav("/dashboard");

  }, [nav]);



  return <Loader />;

}



function Loader() {

  return <div className="loader">Loading...</div>;

}



/* =========================

   REUSABLE FORM COMPONENTS

========================= */



function Field({ label, ...p }) {

  const [showPassword, setShowPassword] = useState(false);

  const isPassword = p.type === "password";



  return (

    <label className={isPassword ? "password-field" : ""}>

      {label}



      {isPassword ? (

        <span className="password-input-wrap">

          <input

            {...p}

            type={showPassword ? "text" : "password"}

          />



          <button

            type="button"

            className="password-toggle"

            aria-label={showPassword ? "Hide password" : "Show password"}

            title={showPassword ? "Hide password" : "Show password"}

            onClick={() => setShowPassword((v) => !v)}

          >

            {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}

          </button>

        </span>

      ) : (

        <input {...p} />

      )}

    </label>

  );

}



const Alert = ({ children, ok }) => (

  <div className={"alert " + (ok ? "ok" : "")}>

    {children}

  </div>

);



/* =========================

   HOMEPAGE

========================= */



function Home() {

  return (

    <>

      <section className="hero">

        <div className="wrap heroGrid">

          <div>

            <div className="eyebrow">

              ● SMART AGRICULTURE, POWERED BY AI

            </div>



            <h1>

              Grow smarter.

              <br />

              <em>Farm with confidence.</em>

            </h1>



            <p>

              Discover suitable crops, get fertilizer guidance, identify

              plant diseases, and explore agricultural products — all in

              one connected platform.

            </p>



            <div className="heroBtns">

              <Link className="btn big" to="/ai-tools">

                Explore AI tools <ArrowUpRight size={18} />

              </Link>



              <Link className="light big" to="/marketplace">

                <Store size={17} /> Marketplace

              </Link>

            </div>

          </div>



          <div className="heroArt">

            <div className="heroImage">

              <img

                src="/assets/images/tomato-growing-geocropai.gif"

                alt="Tomatoes growing on a healthy plant"

                onError={(e) => {

                  e.currentTarget.style.display = "none";

                }}

              />

            </div>



            <div className="float f1">

              <CloudSun size={18} />

              <b>Weather aware</b>

              <small>Temperature · humidity · rainfall</small>

            </div>



            <div className="float f2">

              <BrainCircuit size={18} />

              <b>3 AI tools</b>

              <small>Crop · fertilizer · disease</small>

            </div>

          </div>

        </div>

      </section>



      <section className="wrap section">

        <div className="sectionHead">

          <div>

            <span className="eyebrow">AI TOOLKIT</span>

            <h2>Technology for better farming decisions.</h2>

            <p>Three practical tools to help you get started.</p>

          </div>



          <Link className="text-link" to="/ai-tools">

            View all tools →

          </Link>

        </div>



        <div className="cards">

          <Tool

            icon={<BrainCircuit />}

            title="Crop Recommendation"

            text="Find a suitable crop using soil and weather conditions."

            to="/crop"

          />



          <Tool

            icon={<FlaskConical />}

            title="Fertilizer Guidance"

            text="Compare soil nutrients and receive preliminary guidance."

            to="/fertilizer"

          />



          <Tool

            icon={<ScanSearch />}

            title="Disease Detection"

            text="Upload a leaf image to run plant disease prediction."

            to="/disease"

          />

        </div>



        <div className="sectionCta">

          <Sprout size={21} />

          <span>Explore all three AI tools in one place.</span>

          <Link to="/ai-tools">Open AI toolkit →</Link>

        </div>

      </section>



      <section className="market">

        <div className="wrap marketIn">

          <div>

            <span className="eyebrow">AGRICULTURE MARKETPLACE</span>

            <h2>Farmers list. Buyers discover.</h2>

            <p>

              Connect farm produce with buyers through your agricultural

              marketplace.

            </p>

          </div>



          <Link className="light big" to="/marketplace">

            Browse products →

          </Link>

        </div>

      </section>

    </>

  );

}



/* =========================

   DEDICATED AI TOOLS PAGE

========================= */



function AITools() {

  const tools = [

    {

      number: "01",

      icon: <BrainCircuit size={27} />,

      title: "Crop Recommendation",

      description:

        "Discover suitable crops using soil nutrients, pH, rainfall, temperature and humidity.",

      tags: ["Soil analysis", "Weather-aware"],

      to: "/crop",

      action: "Recommend a crop",

    },

    {

      number: "02",

      icon: <FlaskConical size={27} />,

      title: "Fertilizer Guidance",

      description:

        "Compare NPK levels with crop requirements and receive preliminary nutrient guidance.",

      tags: ["NPK analysis", "Soil nutrients"],

      to: "/fertilizer",

      action: "Explore guidance",

    },

    {

      number: "03",

      icon: <ScanSearch size={27} />,

      title: "Plant Disease Detection",

      description:

        "Upload a leaf image to run your existing plant disease prediction model.",

      tags: ["Leaf image", "AI prediction"],

      to: "/disease",

      action: "Analyze a leaf",

    },

  ];



  return (

    <div className="wrap page ai-hub">

      <section className="ai-hub-hero">

        <span className="eyebrow">GEOCROPAI INTELLIGENCE</span>



        <h1>

          Every farming decision,

          <br />

          <em>smarter.</em>

        </h1>



        <p>

          Explore AI-powered tools for crop selection, nutrient guidance,

          and plant health — all in one place.

        </p>



        <div className="ai-hub-stats">

          <div>

            <strong>03</strong>

            <span>AI tools</span>

          </div>

          <div>

            <strong>01</strong>

            <span>Connected workspace</span>

          </div>

          <div>

            <strong>24/7</strong>

            <span>Platform access</span>

          </div>

        </div>

      </section>



      <section className="ai-hub-section">

        <div className="ai-hub-heading">

          <div>

            <span className="eyebrow">YOUR AI TOOLKIT</span>

            <h2>What would you like to grow better?</h2>

            <p>Select a tool to get started.</p>

          </div>



          <span className="tool-count">03 TOOLS</span>

        </div>



        <div className="ai-hub-grid">

          {tools.map((tool) => (

            <Link

              className="ai-tool-card"

              to={tool.to}

              key={tool.number}

            >

              <div className="ai-tool-top">

                <div className="ai-tool-icon">{tool.icon}</div>

                <span className="ai-tool-number">{tool.number}</span>

              </div>



              <h3>{tool.title}</h3>

              <p>{tool.description}</p>



              <div className="ai-tool-tags">

                {tool.tags.map((tag) => (

                  <span key={tag}>{tag}</span>

                ))}

              </div>



              <div className="ai-tool-action">

                {tool.action}

                <ArrowUpRight size={18} />

              </div>

            </Link>

          ))}

        </div>



        <div className="ai-hub-note">

          <ShieldCheck size={23} />

          <p>

            <strong>Designed for practical farming.</strong>{" "}

            Recommendations depend on the quality of the supplied data.

            Verify agricultural decisions with local expert guidance.

          </p>

        </div>

      </section>

    </div>

  );

}



/* =========================

   REUSABLE TOOL CARD

========================= */



function Tool({ icon, title, text, to }) {

  return (

    <Link className="card" to={to}>

      <div className="icon">{icon}</div>

      <h3>{title}</h3>

      <p>{text}</p>

      <b>Open tool →</b>

    </Link>

  );

}



/* =========================

   AUTHENTICATION

========================= */



function Auth({ title, children }) {

  return (

    <div className="auth">

      <div className="authCard">

        <div className="brand">

          <i><Leaf size={19} /></i>

          Geo<span>Crop</span>AI

        </div>

        <h1>{title}</h1>

        {children}

      </div>

    </div>

  );

}



function Login({ setU }) {

  const [form, set] = useState({ email: "", password: "" });

  const [err, setErr] = useState("");

  const nav = useNavigate();



  async function go(e) {

    e.preventDefault();



    try {

      const d = await api.login(form);



      localStorage.setItem("token", d.access_token);

      localStorage.setItem("user", JSON.stringify(d.user));



      setU(d.user);

      nav("/dashboard");

    } catch (e) {

      setErr(e.message);

    }

  }



  return (

    <Auth title="Welcome back">

      {err && <Alert>{err}</Alert>}



      <form onSubmit={go}>

        <Field

          label="Email"

          type="email"

          required

          value={form.email}

          onChange={(e) => set({ ...form, email: e.target.value })}

        />



        <Field

          label="Password"

          type="password"

          required

          value={form.password}

          onChange={(e) => set({ ...form, password: e.target.value })}

        />



        <button className="btn big full">Sign in</button>

      </form>



      <p className="center">

        New here? <Link to="/signup">Create an account</Link>

      </p>

    </Auth>

  );

}



function Signup({ setU }) {

  const [form, set] = useState({

    username: "",

    email: "",

    password: "",

    role: "farmer",

  });



  const [err, setErr] = useState("");

  const nav = useNavigate();



  async function go(e) {

    e.preventDefault();



    try {

      await api.signup(form);



      const d = await api.login({

        email: form.email,

        password: form.password,

      });



      localStorage.setItem("token", d.access_token);

      localStorage.setItem("user", JSON.stringify(d.user));



      setU(d.user);

      nav("/dashboard");

    } catch (e) {

      setErr(e.message);

    }

  }



  return (

    <Auth title="Create your account">

      {err && <Alert>{err}</Alert>}



      <form onSubmit={go}>

        <Field

          label="Username"

          required

          value={form.username}

          onChange={(e) => set({ ...form, username: e.target.value })}

        />



        <Field

          label="Email"

          type="email"

          required

          value={form.email}

          onChange={(e) => set({ ...form, email: e.target.value })}

        />



        <Field

          label="Password"

          type="password"

          required

          minLength="5"

          value={form.password}

          onChange={(e) => set({ ...form, password: e.target.value })}

        />



        <label>

          Account type

          <select

            value={form.role}

            onChange={(e) => set({ ...form, role: e.target.value })}

          >

            <option value="farmer">Farmer — list produce</option>

            <option value="buyer">Buyer — buy produce</option>

          </select>

        </label>



        <button className="btn big full">Create account</button>

      </form>



      <p className="center">

        Already registered? <Link to="/login">Sign in</Link>

      </p>

    </Auth>

  );

}



/* =========================

   DASHBOARD

========================= */



function Dashboard() {

  const u = user();



  const items = [

    ["🌾", "Crop Recommendation", "Use soil + weather data", "/crop"],

    ["🧪", "Fertilizer Guidance", "Compare NPK", "/fertilizer"],

    ["🌿", "Disease Detection", "Analyze a leaf image", "/disease"],

    ["🛒", "Marketplace", "Browse farm products", "/marketplace"],

    ...(u.role === "farmer"

      ? [

          ["📦", "My Listings", "Manage your products", "/listings"],

          ["🚚", "Seller Orders", "View incoming orders", "/orders"],

        ]

      : [["🧾", "My Orders", "View your purchases", "/orders"]]),

  ];



  return (

    <div className="wrap page">

      <div className="pageHead">

        <span className="eyebrow">YOUR WORKSPACE</span>

        <h1>Hello, {u.username} 👋</h1>

        <p>

          Signed in as <b>{u.role}</b>. Choose what you want to do next.

        </p>

        <Link className="btn" to="/ai-tools">Explore all AI tools →</Link>

      </div>



      <div className="dash">

        {items.map((x) => (

          <Link className="card" to={x[3]} key={x[1]}>

            <div className="emoji">{x[0]}</div>

            <h3>{x[1]}</h3>

            <p>{x[2]}</p>

            <b>Open →</b>

          </Link>

        ))}

      </div>

    </div>

  );

}



/* =========================

   CROP RECOMMENDATION

========================= */



function Crop() {
  const [f, setF] = useState({
    nitrogen: "",
    phosphorus: "",
    potassium: "",
    ph: "",
    rainfall: "",
    city: "",
  });
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [weatherPreview, setWeatherPreview] = useState(null);
  const [weatherLoading, setWeatherLoading] = useState(false);

  async function fetchWeather() {
    if (!f.city.trim()) {
      setError("Enter your city first to fetch weather information.");
      return;
    }
    setWeatherLoading(true);
    setError("");
    try {
      const d = await api.weather(f.city.trim());
      setWeatherPreview(d);
    } catch (err) {
      setError(err.message || "Weather lookup failed. Weather will still be retrieved during recommendation.");
    } finally {
      setWeatherLoading(false);
    }
  }

  async function go(event) {
    event.preventDefault();
    setError("");
    setResult(null);

    const requiredFields = ["nitrogen", "phosphorus", "potassium", "ph", "rainfall"];
    for (const key of requiredFields) {
      const value = String(f[key] ?? "").trim();
      if (!value || !Number.isFinite(Number(value))) {
        setError(`Please enter a valid ${key === "ph" ? "pH" : key} value.`);
        return;
      }
      if (Number(value) < 0) {
        setError(`${key === "ph" ? "pH" : key} cannot be negative.`);
        return;
      }
    }
    if (Number(f.ph) > 14) {
      setError("pH must be between 0 and 14.");
      return;
    }
    if (!f.city.trim()) {
      setError("Please enter your city so local temperature and humidity can be retrieved.");
      return;
    }

    const payload = {
      city: f.city.trim(),
      nitrogen: Number(f.nitrogen),
      phosphorus: Number(f.phosphorus),
      potassium: Number(f.potassium),
      ph: Number(f.ph),
      rainfall: Number(f.rainfall),
    };

    setLoading(true);
    try {
      const data = await api.crop(payload);
      setResult(data);
      if (data.weather) setWeatherPreview(data.weather);
    } catch (err) {
      setError(err.message || "Crop recommendation failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  const topRecommendations = result?.top_recommendations || [];
  const weather = result?.weather || weatherPreview;
  const soil = result?.soil;
  const dataInfo = result?.data_information;

  return (
    <ToolPage
      title="Crop recommendation"
      icon={<BrainCircuit />}
      text="Provide soil readings and your location. Current weather is retrieved automatically; rainfall is the seasonal estimate you enter."
    >
      <form className="panel form" onSubmit={go}>
        {error && <Alert>{error}</Alert>}

        <div className="weather">
          <b><CloudSun size={16} /> Location and current weather</b>
          <div className="inline">
            <input
              placeholder="City e.g. Kolkata"
              value={f.city}
              onChange={(event) => {
                setF((previous) => ({ ...previous, city: event.target.value }));
                setWeatherPreview(null);
              }}
            />
            <button type="button" className="secondary" onClick={fetchWeather} disabled={weatherLoading}>
              {weatherLoading ? "Fetching…" : "Preview weather"}
            </button>
          </div>
          {weatherPreview && (
            <p className="muted">
              {weatherPreview.temperature_celsius ?? weatherPreview.temperature ?? weatherPreview.temp}°C ·
              {weatherPreview.humidity_percent ?? weatherPreview.humidity}% humidity
              {weatherPreview.description ? ` · ${weatherPreview.description}` : ""}
            </p>
          )}
          <small>Weather is fetched by the backend when you submit, even if you do not preview it here.</small>
        </div>

        <h3>Soil measurements</h3>
        <div className="grid2">
          <Field label="Nitrogen (N)" type="number" step="any" min="0" required value={f.nitrogen}
            onChange={(event) => setF({ ...f, nitrogen: event.target.value })} />
          <Field label="Phosphorus (P)" type="number" step="any" min="0" required value={f.phosphorus}
            onChange={(event) => setF({ ...f, phosphorus: event.target.value })} />
          <Field label="Potassium (K)" type="number" step="any" min="0" required value={f.potassium}
            onChange={(event) => setF({ ...f, potassium: event.target.value })} />
          <Field label="Soil pH (0–14)" type="number" step="any" min="0" max="14" required value={f.ph}
            onChange={(event) => setF({ ...f, ph: event.target.value })} />
          <Field label="Seasonal rainfall estimate (mm)" type="number" step="any" min="0" required value={f.rainfall}
            onChange={(event) => setF({ ...f, rainfall: event.target.value })} />
        </div>
        <p className="muted">
          N, P, K and pH should ideally come from a soil test. Rainfall is seasonal—not the current weather or last few hours of rain.
        </p>
        <button className="btn big full" type="submit" disabled={loading}>
          <Sparkles size={16} /> {loading ? "Analyzing conditions…" : "Recommend crops"}
        </button>
      </form>

      {result && (
        <section className="result">
          <div className="resultIcon">🌱</div>
          <span className="eyebrow">MODEL RECOMMENDATION</span>
          <h2>{result.recommended_crop || result.crop || "No crop returned"}</h2>
          <p>Suggested crop based on the submitted soil values and retrieved current weather.</p>

          {topRecommendations.length > 0 && (
            <div className="panel">
              <h3>Other top model suggestions</h3>
              <div className="grid2">
                {topRecommendations.map((item, index) => {
                  const cropName = typeof item === "string" ? item : (item.crop || item.name || item.label);
                  const score = typeof item === "object" ? (item.probability ?? item.confidence ?? item.score) : null;
                  return (
                    <div className="card" key={`${cropName || "crop"}-${index}`}>
                      <b>{index + 1}. {cropName || "Crop"}</b>
                      {score !== null && score !== undefined && (
                        <p>{typeof score === "number" && score <= 1 ? `${(score * 100).toFixed(1)}%` : score}</p>
                      )}
                    </div>
                  );
                })}
              </div>
              <small>Model scores are relative outputs, not guaranteed agronomic success probabilities.</small>
            </div>
          )}

          {weather && (
            <div className="panel">
              <h3><CloudSun size={16} /> Weather retrieved</h3>
              <div className="grid2">
                <div><b>Temperature</b><p>{weather.temperature_celsius ?? weather.temperature ?? weather.temp ?? "—"} °C</p></div>
                <div><b>Humidity</b><p>{weather.humidity_percent ?? weather.humidity ?? "—"}%</p></div>
                <div><b>Conditions</b><p>{weather.description || "—"}</p></div>
                <div><b>Location</b><p>{result.location?.city || f.city}{result.location?.country ? `, ${result.location.country}` : ""}</p></div>
              </div>
            </div>
          )}

          {soil && (
            <div className="panel">
              <h3>Inputs used</h3>
              <div className="grid2">
                <div><b>Nitrogen</b><p>{soil.nitrogen}</p></div>
                <div><b>Phosphorus</b><p>{soil.phosphorus}</p></div>
                <div><b>Potassium</b><p>{soil.potassium}</p></div>
                <div><b>pH</b><p>{soil.ph}</p></div>
                <div><b>Rainfall</b><p>{soil.rainfall_mm ?? soil.rainfall} mm</p></div>
              </div>
            </div>
          )}

          {dataInfo && (
            <div className="panel">
              <h3>Data notes</h3>
              {dataInfo.weather_source && <p><b>Weather source:</b> {dataInfo.weather_source}</p>}
              {dataInfo.rainfall_note && <p>{dataInfo.rainfall_note}</p>}
              {dataInfo.soil_source && <p><b>Soil data:</b> {dataInfo.soil_source}</p>}
              {dataInfo.model_note && <p>{dataInfo.model_note}</p>}
            </div>
          )}
        </section>
      )}
    </ToolPage>
  );
}


/* =========================

   FERTILIZER GUIDANCE

========================= */



function Fertilizer() {
  const [f, setF] = useState({ crop_name: "rice", nitrogen: "", phosphorus: "", potassium: "" });
  const [r, setR] = useState(null);
  const [e, setE] = useState("");
  const [loading, setLoading] = useState(false);
  const crops = ["rice", "maize", "chickpea", "kidneybeans", "pigeonpeas", "mothbeans", "mungbean", "blackgram", "lentil", "pomegranate", "banana", "mango", "grapes", "watermelon", "muskmelon", "apple", "orange", "papaya", "coconut", "cotton", "jute", "coffee"];

  const cropFallback = {
    rice: "NPK 10:26:26", maize: "NPK 10:26:26", wheat: "Urea",
    potato: "MOP (Potash)", cotton: "NPK 10:26:26", banana: "MOP (Potash)",
    sugarcane: "Urea", tomato: "NPK 19:19:19", grapes: "NPK 19:19:19",
    pomegranate: "NPK 19:19:19", apple: "NPK 19:19:19", orange: "NPK 19:19:19",
    papaya: "NPK 19:19:19", watermelon: "NPK 19:19:19", muskmelon: "NPK 19:19:19",
    coconut: "NPK 10:26:26", coffee: "NPK 10:26:26", jute: "Urea",
    chickpea: "DAP", kidneybeans: "DAP", pigeonpeas: "DAP", mothbeans: "DAP",
    mungbean: "DAP", blackgram: "DAP", lentil: "DAP", default: "NPK 19:19:19",
  };

  function npkFallback() {
    const vals = { N: Number(f.nitrogen), P: Number(f.phosphorus), K: Number(f.potassium) };
    const min = Math.min(vals.N, vals.P, vals.K);
    const max = Math.max(vals.N, vals.P, vals.K);
    if (!Number.isFinite(min) || max === min || (max - min) / Math.max(max, 1) < 0.12) {
      return cropFallback[f.crop_name.toLowerCase()] || cropFallback.default;
    }
    if (min === vals.N) return "Urea";
    if (min === vals.P) return "DAP";
    return "MOP (Potash)";
  }

  function specificRecommendation(apiRecommendation) {
    const fallback = npkFallback();
    const apiName = typeof apiRecommendation === "string" ? apiRecommendation.trim() : "";
    if (!apiName || /^(npk compound fertilizer|compound fertilizer|npk fertilizer|general fertilizer)$/i.test(apiName)) return fallback;
    return apiName;
  }

  async function go(event) {
    event.preventDefault();
    setE("");
    setR(null);
    const vals = [f.nitrogen, f.phosphorus, f.potassium];
    if (vals.some(v => v === "" || !Number.isFinite(Number(v)) || Number(v) < 0)) {
      setE("Enter valid non-negative values for all three NPK nutrients.");
      return;
    }
    setLoading(true);
    try {
      const data = await api.fertilizer({
        crop_name: f.crop_name,
        nitrogen: Number(f.nitrogen),
        phosphorus: Number(f.phosphorus),
        potassium: Number(f.potassium),
      });
      setR(data);
    } catch (error) {
      setR(null);
      setE(error?.message || "Unable to get a fertilizer recommendation. Check that the backend is running.");
    } finally {
      setLoading(false);
    }
  }

  const recommendation = specificRecommendation(
    r?.recommended_fertilizer || r?.fertilizer_name || r?.recommendation
  );
  const alternatives = r?.alternative_fertilizers || r?.alternatives || [];
  const analysis = r?.nutrient_analysis || {};
  const nutrientConfig = [
    { key: "N", aliases: ["N", "nitrogen"], label: "Nitrogen (N)", entered: f.nitrogen },
    { key: "P", aliases: ["P", "phosphorus"], label: "Phosphorus (P)", entered: f.phosphorus },
    { key: "K", aliases: ["K", "potassium"], label: "Potassium (K)", entered: f.potassium },
  ];
  const getAnalysisItem = (nutrient) => {
    for (const key of nutrient.aliases) {
      if (analysis?.[key]) return analysis[key];
    }
    return null;
  };
  const hasAnalysis = nutrientConfig.some(n => getAnalysisItem(n));
  const reason = r?.reason || `Prediction generated for ${f.crop_name} using the entered NPK values.`;
  const confidence = Number(r?.confidence);
  const confidencePercent = Number.isFinite(confidence) ? `${Math.round(confidence * 100)}%` : null;

  return (
    <ToolPage title="Fertilizer recommendation" icon={<FlaskConical />} text="Get a fertilizer prediction using the selected crop and NPK inputs.">
      <form className="panel form" onSubmit={go}>
        {e && <Alert>{e}</Alert>}
        <label>Crop
          <select value={f.crop_name} onChange={event => setF({ ...f, crop_name: event.target.value })}>
            {crops.map(crop => <option key={crop} value={crop}>{crop}</option>)}
          </select>
        </label>
        <div className="grid3">
          {[["nitrogen", "N — nitrogen"], ["phosphorus", "P — phosphorus"], ["potassium", "K — potassium"]].map(([key, label]) => (
            <Field key={key} label={label} type="number" min="0" step="any" required value={f[key]} onChange={event => setF({ ...f, [key]: event.target.value })} />
          ))}
        </div>
        <button className="btn big full" type="submit" disabled={loading}>
          <Sparkles size={16} /> {loading ? "Finding fertilizer…" : "Get recommendation"}
        </button>
      </form>

      <Result title={r ? `Fertilizer suggestions for ${f.crop_name}` : "Fertilizer guidance"} value={r ? null : "Enter NPK values to get a recommendation"} empty={!r}>
        {r && <div className="recommend" style={{ paddingTop: 12 }}>
          <div className="panel" style={{ padding: 24, margin: "8px 0 16px", overflow: "visible" }}>
            <div style={{ fontSize: "0.85rem", opacity: 0.75, marginBottom: 8 }}>RECOMMENDED FERTILIZER</div>
            <h2 style={{ margin: "0 0 12px", color: "#14532d", lineHeight: 1.25, overflowWrap: "anywhere" }}>{recommendation}</h2>
            <p style={{ margin: 0, lineHeight: 1.65 }}>{reason}</p>
            {confidencePercent && <p style={{ margin: "12px 0 0" }}><b>Model confidence:</b> {confidencePercent}</p>}
          </div>

          <div className="panel" style={{ padding: 16, marginBottom: 12 }}>
            <b>Entered NPK values</b>
            <div className="grid3" style={{ marginTop: 12 }}>
              {[["Nitrogen (N)", f.nitrogen], ["Phosphorus (P)", f.phosphorus], ["Potassium (K)", f.potassium]].map(([label, value]) => (
                <div key={label}><small>{label}</small><div style={{ fontSize: "1.2rem", fontWeight: 700 }}>{value}</div></div>
              ))}
            </div>
          </div>

          <div className="panel" style={{ padding: 16, marginBottom: 12 }}>
            <b>NPK reference comparison</b>
            {hasAnalysis ? (
              <div className="grid3" style={{ marginTop: 12 }}>
                {nutrientConfig.map(nutrient => {
                  const item = getAnalysisItem(nutrient) || {};
                  const reference = item.reference ?? item.reference_value ?? item.required ?? item.target;
                  const entered = item.soil_value ?? item.entered_value ?? item.input_value ?? nutrient.entered;
                  const difference = item.difference ?? item.diff;
                  const status = item.status ?? item.label ?? "Unavailable";
                  return (
                    <div key={nutrient.key} className="panel" style={{ padding: 12, margin: 0 }}>
                      <b>{nutrient.label}</b>
                      <div style={{ marginTop: 8 }}><small>Entered value</small><div style={{ fontWeight: 700 }}>{entered ?? "—"}</div></div>
                      <div style={{ marginTop: 6 }}><small>Reference</small><div style={{ fontWeight: 700 }}>{reference ?? "—"}</div></div>
                      <div style={{ marginTop: 6 }}><small>Difference</small><div style={{ fontWeight: 700 }}>{difference ?? "—"}</div></div>
                      <div style={{ marginTop: 8, color: "#15803d", fontWeight: 700 }}>{status}</div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p style={{ margin: "10px 0 0", lineHeight: 1.6 }}>
                Reference values and nutrient comparison are not provided by the current backend response. The model prediction is based on crop and NPK inputs; it should not be interpreted as a soil deficiency analysis.
              </p>
            )}
          </div>

          {Array.isArray(alternatives) && alternatives.length > 0 && (
            <p style={{ margin: "12px 0" }}><b>Alternative predictions:</b> {alternatives.map(x => typeof x === "string" ? x : x?.name || x?.fertilizer).filter(Boolean).join(", ")}</p>
          )}
          {r?.note && <p style={{ margin: "12px 0 4px", fontSize: "0.88rem", opacity: 0.75, lineHeight: 1.6 }}>{r.note}</p>}
          <p style={{ margin: "12px 0 4px", fontSize: "0.88rem", opacity: 0.75, lineHeight: 1.6 }}>General project guidance only. Verify fertilizer choice and application rate with soil testing and local agricultural recommendations.</p>
        </div>}
      </Result>
    </ToolPage>
  );
}

/* =========================

   DISEASE DETECTION

========================= */



function Disease() {

  const [file, setFile] = useState(null);

  const [preview, setPreview] = useState("");

  const [r, setR] = useState(null);

  const [e, setE] = useState("");



  async function go(e) {

    e.preventDefault();



    if (!file) {

      setE("Choose a leaf image first.");

      return;

    }



    try {

      setE("");

      setR(await api.disease(file));

    } catch (x) {

      setE(x.message);

    }

  }



  return (

    <ToolPage

      title="Plant disease detection"

      icon={<ScanSearch />}

      text="Upload a leaf image and use the existing disease prediction model."

    >

      <form className="panel form" onSubmit={go}>

        {e && <Alert>{e}</Alert>}



        <label className="upload">

          {preview ? (

            <img src={preview} alt="Selected leaf preview" />

          ) : (

            <>

              <UploadCloud size={40} />

              <b>Choose a leaf image</b>

              <small>PNG, JPG or JPEG</small>

            </>

          )}



          <input

            type="file"

            accept="image/*"

            onChange={(e) => {

              const selected = e.target.files?.[0];



              if (selected) {

                setFile(selected);

                setPreview(URL.createObjectURL(selected));

                setR(null);

                setE("");

              }

            }}

          />

        </label>



        <button className="btn big full">

          <Sparkles size={16} /> Detect disease

        </button>

      </form>



      <Result

        title="Prediction"

        value={r?.prediction || "Upload an image"}

        empty={!r}

      >

        {r && (

          <div

            className="recommend"

            dangerouslySetInnerHTML={{ __html: r.disease_info }}

          />

        )}

      </Result>

    </ToolPage>

  );

}



/* =========================

   TOOL PAGE AND RESULTS

========================= */



function ToolPage({ title, icon, text, children }) {

  return (

    <div className="wrap page">

      <div className="pageHead toolTitle">

        <div className="bigIcon">{icon}</div>

        <div>

          <span className="eyebrow">AI TOOL</span>

          <h1>{title}</h1>

          <p>{text}</p>

        </div>

      </div>



      <div className="twoCol">{children}</div>

    </div>

  );

}



function Result({ title, value, empty, children }) {

  return (

    <section className="result">

      <div className="resultIcon">🌱</div>

      <span className="eyebrow">{title}</span>

      {value && <h2>{value}</h2>}

      {empty ? <p>Your result will appear here.</p> : children}

    </section>

  );

}



/* =========================

   MARKETPLACE

========================= */



function Market() {

  const [ps, setPs] = useState([]);

  const [q, setQ] = useState("");

  const [e, setE] = useState("");



  async function load() {

    try {

      setPs((await api.products()).products || []);

      setE("");

    } catch (x) {

      setE(x.message);

    }

  }



  useEffect(() => {

    load();

  }, []);



  const shown = ps.filter((p) =>

    `${p.name} ${p.category} ${p.location}`

      .toLowerCase()

      .includes(q.toLowerCase())

  );



  return (

    <div className="wrap page">

      <div className="marketHead">

        <div>

          <span className="eyebrow">AGRICULTURE MARKETPLACE</span>

          <h1>Fresh from the farm.</h1>

          <p>Browse farmer listings. Payment gateway is not included yet.</p>

        </div>



        <Link className="btn" to="/sell">

          <PackagePlus size={16} /> List my produce

        </Link>

      </div>



      {e && <Alert>{e}</Alert>}



      <div className="search">

        <Store size={17} />

        <input

          placeholder="Search products or locations..."

          value={q}

          onChange={(e) => setQ(e.target.value)}

        />

      </div>



      <div className="products">

        {shown.map((p) => (

          <Product key={p.id} p={p} reload={load} />

        ))}



        {!shown.length && (

          <div className="empty">

            <span>🌾</span>

            <h2>No products found</h2>

          </div>

        )}

      </div>

    </div>

  );

}



function Product({ p, reload }) {
  const u = user();
  const [orderOpen, setOrderOpen] = useState(false);
  const [quantity, setQuantity] = useState("1");
  const [busy, setBusy] = useState(false);
  const [orderError, setOrderError] = useState("");
  const [orderSuccess, setOrderSuccess] = useState("");

  const available = Number(p.quantity) || 0;
  const price = Number(p.price) || 0;
  const qty = Number(quantity);
  const total = Number.isFinite(qty) && qty > 0 ? qty * price : 0;

  function openOrder() {
    if (!u) {
      window.alert("Please log in as a buyer to place an order.");
      return;
    }
    if (u.role !== "buyer") {
      window.alert("Only buyer accounts can place orders.");
      return;
    }
    setQuantity("1");
    setOrderError("");
    setOrderSuccess("");
    setOrderOpen(true);
  }

  async function placeOrder(event) {
    event.preventDefault();
    setOrderError("");
    if (!Number.isInteger(qty) || qty < 1) {
      setOrderError("Enter a whole-number quantity of at least 1.");
      return;
    }
    if (qty > available) {
      setOrderError(`Only ${available} ${p.unit} available.`);
      return;
    }

    try {
      setBusy(true);
      const result = await api.order({ product_id: p.id, quantity: qty });
      setOrderSuccess(`Order placed successfully. Total: ₹${Number(result.total_price).toFixed(2)}.`);
      await reload();
    } catch (error) {
      setOrderError(error.message || "Could not place the order.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <article
        className="product"
        style={{
          display: "flex",
          flexDirection: "column",
          height: "100%",
          minWidth: 0,
          overflow: "hidden",
          borderRadius: "22px",
        }}
      >
        <div
          className="prodImg"
          style={{
            display: "block",
            position: "relative",
            flex: "0 0 265px",
            height: "265px",
            minHeight: "265px",
            overflow: "hidden",
            background: "#e5efe3",
          }}
        >
          {p.image_url ? (
            <img
              src={p.image_url}
              alt={p.name}
              loading="lazy"
              onError={(event) => {
                event.currentTarget.style.display = "none";
              }}
              style={{
                display: "block",
                width: "100%",
                height: "100%",
                maxWidth: "100%",
                objectFit: "cover",
                objectPosition: "center",
              }}
            />
          ) : (
            <span
              style={{
                display: "grid",
                width: "100%",
                height: "100%",
                placeItems: "center",
                fontSize: "48px",
              }}
            >
              🌱
            </span>
          )}
        </div>

        <div
          className="prodBody"
          style={{
            display: "flex",
            flex: "1 1 auto",
            flexDirection: "column",
            minWidth: 0,
            padding: "20px 22px",
            background: "#fff",
          }}
        >
          <small style={{ position: "static", display: "block", marginBottom: "10px" }}>
            {p.category}
          </small>
          <h3 style={{ marginTop: 0 }}>{p.name}</h3>
          <p>{p.description || "Fresh farm product."}</p>
          <div className="muted">
            <MapPin size={13} /> {p.location}
          </div>
          <p style={{ margin: "12px 0 0", color: "#326b4e", fontSize: "13px", fontWeight: 600 }}>
            Available: {p.quantity ?? 0} {p.unit || "kg"}
          </p>

          <div
            className="prodBottom"
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "12px",
              marginTop: "auto",
              paddingTop: "16px",
              borderTop: "1px solid #e5ece5",
            }}
          >
            <b>
              ₹{price.toFixed(2)}
              <small>/{p.unit}</small>
            </b>
            <button className="btn small" type="button" onClick={openOrder}>
              <ShoppingCart size={14} /> Buy
            </button>
          </div>
        </div>
      </article>

      {orderOpen && (
        <div
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget && !busy) setOrderOpen(false);
          }}
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 1000,
            display: "grid",
            placeItems: "center",
            padding: "20px",
            background: "rgba(18, 35, 24, 0.62)",
            backdropFilter: "blur(4px)",
          }}
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby={`order-title-${p.id}`}
            style={{
              width: "min(100%, 440px)",
              background: "#fffdf7",
              color: "#24382a",
              borderRadius: "20px",
              padding: "26px",
              boxShadow: "0 24px 80px rgba(0,0,0,.25)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", gap: "16px", alignItems: "start" }}>
              <div>
                <span className="eyebrow">ORDER SUMMARY</span>
                <h2 id={`order-title-${p.id}`} style={{ margin: "8px 0" }}>Buy {p.name}</h2>
                <p style={{ margin: 0, color: "#68756b" }}>
                  ₹{price.toFixed(2)} per {p.unit} · {available} {p.unit} available
                </p>
              </div>
              <button
                type="button"
                className="ghost"
                aria-label="Close order dialog"
                onClick={() => setOrderOpen(false)}
                disabled={busy}
              >
                ×
              </button>
            </div>

            {orderSuccess ? (
              <div style={{ marginTop: "20px" }}>
                <Alert ok>{orderSuccess}</Alert>
                <button
                  className="btn big full"
                  type="button"
                  onClick={() => {
                    setOrderOpen(false);
                    setOrderSuccess("");
                  }}
                >
                  Done
                </button>
              </div>
            ) : (
              <form onSubmit={placeOrder} style={{ marginTop: "22px" }}>
                {orderError && <Alert>{orderError}</Alert>}
                <label>
                  Quantity ({p.unit})
                  <input
                    type="number"
                    min="1"
                    max={available}
                    step="1"
                    required
                    value={quantity}
                    onChange={(event) => setQuantity(event.target.value)}
                    disabled={busy}
                    autoFocus
                  />
                </label>

                <div style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  margin: "18px 0 22px",
                  padding: "14px 16px",
                  borderRadius: "12px",
                  background: "#edf4e8",
                }}>
                  <span>Estimated total</span>
                  <strong style={{ fontSize: "1.3rem" }}>₹{total.toFixed(2)}</strong>
                </div>

                <div style={{ display: "flex", gap: "10px" }}>
                  <button
                    className="secondary"
                    type="button"
                    onClick={() => setOrderOpen(false)}
                    disabled={busy}
                    style={{ flex: 1 }}
                  >
                    Cancel
                  </button>
                  <button className="btn big" type="submit" disabled={busy || available < 1} style={{ flex: 1 }}>
                    {busy ? "Placing order..." : "Confirm order"}
                  </button>
                </div>
              </form>
            )}
          </section>
        </div>
      )}
    </>
  );
}


function Sell() {
  const [f, setF] = useState({
    name: "",
    category: "Vegetables",
    description: "",
    price: "",
    quantity: "",
    unit: "kg",
    location: "",
  });
  const [image, setImage] = useState(null);
  const [preview, setPreview] = useState("");
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  function chooseImage(event) {
    const file = event.target.files?.[0];
    setErr("");
    setMsg("");
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      setErr("Please select an image file.");
      event.target.value = "";
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setErr("Please choose an image smaller than 5 MB.");
      event.target.value = "";
      return;
    }

    if (preview) URL.revokeObjectURL(preview);
    setImage(file);
    setPreview(URL.createObjectURL(file));
  }

  async function go(event) {
    event.preventDefault();
    setMsg("");
    setErr("");

    if (!image) {
      setErr("Please browse and select a product image before publishing.");
      return;
    }

    if (!f.name.trim() || !f.category.trim() || !f.location.trim()) {
      setErr("Please fill in the product name, category, and location.");
      return;
    }

    if (!(Number(f.price) > 0) || !(Number(f.quantity) > 0)) {
      setErr("Price and available quantity must be greater than zero.");
      return;
    }

    if (typeof api.uploadProduct !== "function") {
      setErr("api.uploadProduct is missing. Check frontend/src/api.js.");
      return;
    }

    setBusy(true);

    try {
      const product = {
        ...f,
        name: f.name.trim(),
        description: f.description.trim(),
        location: f.location.trim(),
        price: Number(f.price),
        quantity: Number(f.quantity),
      };

      // Send the image and product details to FastAPI. The backend uploads it to Cloudinary.
      await api.uploadProduct(product, image);

      setMsg("Product and image uploaded successfully.");
      setF({
        name: "",
        category: "Vegetables",
        description: "",
        price: "",
        quantity: "",
        unit: "kg",
        location: "",
      });
      setImage(null);

      if (preview) URL.revokeObjectURL(preview);
      setPreview("");

      const input = document.getElementById("product-image-input");
      if (input) input.value = "";
    } catch (error) {
      setErr(error.message || "Could not publish the product. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="wrap page">
      <div className="pageHead">
        <span className="eyebrow">FARMER WORKSPACE</span>
        <h1>List your produce</h1>
        <p>Choose a product photo from your device and publish your listing.</p>
      </div>

      {msg && <Alert ok>{msg}</Alert>}
      {err && <Alert>{err}</Alert>}

      <form className="panel form" onSubmit={go}>
        <div className="grid2">
          <Field
            label="Product name"
            required
            value={f.name}
            onChange={(event) => setF({ ...f, name: event.target.value })}
          />

          <label>
            Category
            <select
              required
              value={f.category}
              onChange={(event) => setF({ ...f, category: event.target.value })}
            >
              <option>Vegetables</option>
              <option>Fruits</option>
              <option>Grains</option>
              <option>Pulses</option>
              <option>Other</option>
            </select>
          </label>

          <Field
            label="Price (₹ per unit)"
            type="number"
            min="0.01"
            step="0.01"
            required
            value={f.price}
            onChange={(event) => setF({ ...f, price: event.target.value })}
          />

          <Field
            label="Available quantity"
            type="number"
            min="0.01"
            step="0.01"
            required
            value={f.quantity}
            onChange={(event) => setF({ ...f, quantity: event.target.value })}
          />

          <Field
            label="Location"
            required
            value={f.location}
            onChange={(event) => setF({ ...f, location: event.target.value })}
          />
        </div>

        <label>
          Unit
          <select
            value={f.unit}
            onChange={(event) => setF({ ...f, unit: event.target.value })}
          >
            <option>kg</option>
            <option>quintal</option>
            <option>ton</option>
            <option>piece</option>
          </select>
        </label>

        <label>
          Product image
          <input
            id="product-image-input"
            type="file"
            accept="image/*"
            required
            onChange={chooseImage}
          />
          <span className="muted">
            Choose a photo from your device. Maximum size: 5 MB.
          </span>
        </label>

        {preview && (
          <div style={{ margin: "12px 0 18px" }}>
            <img
              src={preview}
              alt="Selected product preview"
              style={{
                display: "block",
                width: "min(100%, 320px)",
                maxHeight: "240px",
                objectFit: "cover",
                borderRadius: "12px",
                border: "1px solid #d6e4d8",
              }}
            />
            <button
              type="button"
              className="btn secondary"
              style={{ marginTop: "10px" }}
              onClick={() => {
                if (preview) URL.revokeObjectURL(preview);
                setPreview("");
                setImage(null);
                const input = document.getElementById("product-image-input");
                if (input) input.value = "";
              }}
            >
              Remove image
            </button>
          </div>
        )}

        <label>
          Description
          <textarea
            rows="5"
            value={f.description}
            onChange={(event) => setF({ ...f, description: event.target.value })}
          />
        </label>

        <button className="btn big" type="submit" disabled={busy}>
          {busy ? "Uploading image and publishing..." : "Publish listing"}
        </button>
      </form>
    </div>
  );
}

function Listings() {

  const [d, setD] = useState(null);



  useEffect(() => {

    api.listings()

      .then(setD)

      .catch((e) => setD({ error: e.message }));

  }, []);



  return (

    <div className="wrap page">

      <div className="pageHead">

        <span className="eyebrow">FARMER WORKSPACE</span>

        <h1>My listings</h1>

      </div>



      {!d ? (

        <Loader />

      ) : d.error ? (

        <Alert>{d.error}</Alert>

      ) : (

        <div className="list">

          {(d.products || []).map((p) => (

            <div className="row" key={p.id}>

              <b>{p.name}</b>

              <span>{p.category} · {p.location}</span>

              <span>{p.quantity} {p.unit}</span>

              <b>₹{p.price}/{p.unit}</b>

            </div>

          ))}

        </div>

      )}

    </div>

  );

}



function Orders() {

  const u = user();

  const [d, setD] = useState(null);



  useEffect(() => {

    (u.role === "farmer" ? api.sellerOrders() : api.orders())

      .then(setD)

      .catch((e) => setD({ error: e.message }));

  }, []);



  return (

    <div className="wrap page">

      <div className="pageHead">

        <span className="eyebrow">

          {u.role === "farmer" ? "FARMER" : "BUYER"} WORKSPACE

        </span>

        <h1>{u.role === "farmer" ? "Seller orders" : "My orders"}</h1>

      </div>



      {!d ? (

        <Loader />

      ) : d.error ? (

        <Alert>{d.error}</Alert>

      ) : (

        <div className="list">

          {(d.orders || []).map((o) => (

            <div className="row" key={o.id}>

              <b>{o.product_name}</b>

              <span>{u.role === "farmer" ? o.buyer_email : o.seller_email}</span>

              <span>{o.quantity} {o.unit}</span>

              <b>₹{o.total_price}</b>

              <em>{o.status}</em>

            </div>

          ))}

        </div>

      )}

    </div>

  );

}



/* =========================

   NOT FOUND

========================= */



function NotFound() {

  return (

    <div className="empty page">

      <span>🌱</span>

      <h1>Page not found</h1>

      <Link className="btn" to="/">Back home</Link>

    </div>

  );

}



export default Layout;
