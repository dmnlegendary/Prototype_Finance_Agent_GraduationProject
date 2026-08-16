import React, { useState, useEffect, useRef } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine,
  Area, AreaChart, ComposedChart, Line
} from 'recharts';


Hola

/*** 
const tokens = {
  "--color-primary":       "#7c3aed",
  "--color-primary-light": "#ede9fe",
  "--color-primary-dark":  "#5b21b6",
  "--color-accent":        "#f59e0b",
  "--color-success":       "#16a34a",
  "--color-success-light": "#dcfce7",
  "--color-danger":        "#dc2626",
  "--color-danger-light":  "#fee2e2",
  "--color-warning":       "#d97706",
  "--color-warning-light": "#fef3c7",
  "--color-info":          "#0ea5e9",
  "--color-info-light":    "#e0f2fe",
  "--color-bg":            "#f8f7ff",
  "--color-surface":       "#ffffff",
  "--color-border":        "#e5e7eb",
  "--color-text":          "#1f2937",
  "--color-text-muted":    "#6b7280",
  "--color-pink-light":    "#fce7f3",
  "--color-pink":          "#ec4899",
  "--color-green-dark":    "#166534",
  "--color-green-light":   "#bbf7d0",
  "--radius":              "12px",
  "--radius-sm":           "8px",
  "--shadow":              "0 2px 12px rgba(0,0,0,0.08)",
  "--shadow-lg":           "0 8px 32px rgba(0,0,0,0.14)",
};

const mockProductos = [
  { nombre:"Leche Lala 1L",   costo:18, precio:22 },
  { nombre:"Pan Bimbo",       costo:35, precio:42 },
  { nombre:"Coca-Cola 600ml", costo:14, precio:18 },
  { nombre:"Sabritas",        costo:12, precio:16 },
];

const reporteData = [
  { mes:"Ene", ingresos:42000, egresos:31000, utilidad:11000 },
  { mes:"Feb", ingresos:38000, egresos:29000, utilidad:9000  },
  { mes:"Mar", ingresos:45000, egresos:33000, utilidad:12000 },
  { mes:"Abr", ingresos:41000, egresos:35000, utilidad:6000  },
  { mes:"May", ingresos:48000, egresos:32000, utilidad:16000 },
  { mes:"Jun", ingresos:51000, egresos:34000, utilidad:17000 },
];

const categoriasForecast = [
  { cat:"Bebidas",   productos:["Coca-Cola 600ml","Agua 1.5L","Jugo Del Valle","Cerveza Modelo"] },
  { cat:"Lácteos",   productos:["Leche Lala 1L","Yogurt Alpura","Queso Oaxaca"] },
  { cat:"Botanas",   productos:["Sabritas","Doritos","Ruffles","Palomitas"] },
  { cat:"Panadería", productos:["Pan Bimbo","Gansito","Submarino"] },
  { cat:"Abarrotes", productos:["Arroz 1kg","Frijol 1kg","Aceite 1L","Sal 1kg"] },
];

const fmt = (n) => `$${Number(n).toLocaleString("es-MX", {minimumFractionDigits:0})}`;

const aviMessages = {
  home:      "👋 Hola Don Raúl. Hoy tus ventas van bien. ¿Quieres ver el pronóstico de esta semana o revisar tus gastos?",
  gastos:    "📝 Registra tus gastos fijos (renta, luz, internet) y variables (inventario, merma). Entre más datos tengas, más preciso será tu punto de equilibrio.",
  equilibrio:"⚖️ La calidad de tu punto de equilibrio depende directamente de qué tan bien registres tus gastos fijos y variables. ¡Cada peso cuenta!",
  precios:   "💡 El precio sugerido se calcula con una fórmula basada en tu costo de compra más un margen de ganancia.",
  forecast:  "📈 El pronóstico lo genera un modelo de Machine Learning externo entrenado con tu historial de ventas. Yo solo te ayudo a interpretarlo.",
  reportes:  "📊 Abril fue tu mes más ajustado. El gasto subió pero las ventas no acompañaron. ¿Quieres revisar qué pasó?",
};

const gastosIniciales = {
  fijos: [
    { id:1, concepto:"Renta",    monto:4500, nota:"Mensual" },
    { id:2, concepto:"Luz",      monto:820,  nota:"Bimestral prorrateado" },
    { id:3, concepto:"Internet", monto:350,  nota:"Fibra óptica" },
    { id:4, concepto:"Gas",      monto:280,  nota:"" },
  ],
  variables: [
    { id:1, concepto:"Inventario de productos", monto:114567, nota:"Compras del mes" },
    { id:2, concepto:"Merma y caducidades",     monto:2300,  nota:"Estimado" },
    { id:3, concepto:"Bolsas y empaque",        monto:480,   nota:"" },
    { id:4, concepto:"Comisiones de pago",      monto:620,   nota:"Terminal" },
  ],
};

const inputStyle = {
  width:"100%", padding:"9px 12px", borderRadius:"8px",
  border:"1.5px solid #e5e7eb", fontSize:13,
  outline:"none", background:"#f8f7ff", color:"#1f2937", boxSizing:"border-box"
};
const labelStyle = { fontSize:12, fontWeight:600, color:"#6b7280" };
const btnPrimary = {
  padding:"9px 16px", borderRadius:"8px", border:"none",
  background:"#7c3aed", color:"#fff", fontWeight:600, fontSize:13, cursor:"pointer", width:"100%"
};
const btnSecondary = {
  padding:"9px 16px", borderRadius:"8px",
  border:"1.5px solid #7c3aed", background:"transparent",
  color:"#7c3aed", fontWeight:600, fontSize:13, cursor:"pointer", width:"100%"
};
const btnDanger = {
  padding:"9px 16px", borderRadius:"8px", border:"none",
  background:"#dc2626", color:"#fff", fontWeight:600, fontSize:13, cursor:"pointer", width:"100%"
};
const badge = { borderRadius:12, padding:"2px 10px", fontSize:11, fontWeight:600, display:"inline-block" };

function Card({ title, children }) {
  return (
    <div style={{ background:"#ffffff", borderRadius:"12px", boxShadow:"0 2px 12px rgba(0,0,0,0.08)", border:"1px solid #e5e7eb", padding:16 }}>
      {title && <div style={{ fontWeight:700, fontSize:14, marginBottom:12, paddingBottom:8, borderBottom:"1px solid #e5e7eb" }}>{title}</div>}
      {children}
    </div>
  );
}

function SectionHeader({ icon, title, subtitle }) {
  return (
    <div>
      <h2 style={{ margin:0, fontSize:18, fontWeight:700 }}>{icon} {title}</h2>
      {subtitle && <p style={{ margin:"4px 0 0", color:"#6b7280", fontSize:13 }}>{subtitle}</p>}
    </div>
  );
}

function Toast({ msg }) {
  return (
    <div style={{ position:"fixed", bottom:24, left:"50%", transform:"translateX(-50%)",
                  background:"#1f2937", color:"#fff", padding:"10px 20px",
                  borderRadius:20, fontSize:13, fontWeight:600, zIndex:999,
                  boxShadow:"0 8px 32px rgba(0,0,0,0.14)", whiteSpace:"nowrap" }}>{msg}</div>
  );
}

/* ── HOME DASHBOARD ── */
/*
const ventasSemana = [
  { d:"Lun", v:3200 }, { d:"Mar", v:2800 }, { d:"Mié", v:4100 },
  { d:"Jue", v:3600 }, { d:"Vie", v:4800 }, { d:"Sáb", v:5200 }, { d:"Dom", v:3900 },
];
const gastosPreview = [
  { name:"Fijos", total:5950 }, { name:"Variables", total:117967 },
];
const forecastPreview = [
  { cat:"Bebidas", uds:142 }, { cat:"Lácteos", uds:87 }, { cat:"Botanas", uds:110 }, { cat:"Abarrotes", uds:95 },
];
const utilidadPreview = [
  { mes:"Ene", u:11000 }, { mes:"Feb", u:9000 }, { mes:"Mar", u:12000 },
  { mes:"Abr", u:6000  }, { mes:"May", u:16000 }, { mes:"Jun", u:17000 },
];

function HomeView({ setActiveTab }) {
  const kpis = [
    { label:"Ventas hoy",       value:"$3,240",  delta:"+8% vs ayer",    up:true  },
    { label:"Gastos del mes",   value:"$123,917", delta:"+2% vs mes ant", up:false },
    { label:"Utilidad neta",    value:"$17,000", delta:"+6% vs mes ant",  up:true  },
    { label:"Punto equilibrio", value:"$28,500", delta:"meta mensual",    up:null  },
  ];

  const dashCards = [
    {
      id:"reportes", icon:"📊", label:"Reportes financieros",
      color:"#fce7f3", border:"#ec4899",
      badge:"Jun: mejor mes", badgeColor:"#16a34a",
      chart: (
        <ResponsiveContainer width="100%" height={75}>
          <AreaChart data={utilidadPreview} margin={{top:4,right:4,left:-30,bottom:0}}>
            <defs>
              <linearGradient id="hg1" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#ec4899" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#ec4899" stopOpacity={0.02}/>
              </linearGradient>
            </defs>
            <XAxis dataKey="mes" tick={{fontSize:9}} axisLine={false} tickLine={false}/>
            <Tooltip formatter={v=>`$${(v/1000).toFixed(0)}k`} contentStyle={{fontSize:11}}/>
            <Area type="monotone" dataKey="u" stroke="#ec4899" fill="url(#hg1)" strokeWidth={2} dot={false}/>
          </AreaChart>
        </ResponsiveContainer>
      ),
    },
    {
      id:"forecast", icon:"📈", label:"Pronóstico de ventas",
      color:"#f3e8ff", border:"#7c3aed",
      badge:"Modelo ML · 24 sem.", badgeColor:"#7c3aed",
      chart: (
        <ResponsiveContainer width="100%" height={75}>
          <BarChart data={forecastPreview} margin={{top:4,right:4,left:-30,bottom:0}}>
            <XAxis dataKey="cat" tick={{fontSize:9}} axisLine={false} tickLine={false}/>
            <Tooltip formatter={v=>`${v} uds`} contentStyle={{fontSize:11}}/>
            <Bar dataKey="uds" fill="#7c3aed" radius={[3,3,0,0]}/>
          </BarChart>
        </ResponsiveContainer>
      ),
    },
    {
      id:"gastos", icon:"📝", label:"Registrar gastos",
      color:"#dcfce7", border:"#16a34a",
      badge:"8 gastos registrados", badgeColor:"#16a34a",
      chart: (
        <ResponsiveContainer width="100%" height={75}>
          <BarChart data={gastosPreview} margin={{top:4,right:4,left:-30,bottom:0}}>
            <XAxis dataKey="name" tick={{fontSize:9}} axisLine={false} tickLine={false}/>
            <Tooltip formatter={v=>`$${(v/1000).toFixed(0)}k`} contentStyle={{fontSize:11}}/>
            <Bar dataKey="total" fill="#16a34a" radius={[3,3,0,0]}/>
          </BarChart>
        </ResponsiveContainer>
      ),
    },
    {
      id:"equilibrio", icon:"⚖️", label:"Punto de equilibrio",
      color:"#bbf7d0", border:"#166534",
      badge:"Calidad: Alta ✅", badgeColor:"#166534",
      chart: (
        <ResponsiveContainer width="100%" height={75}>
          <AreaChart data={ventasSemana} margin={{top:4,right:4,left:-30,bottom:0}}>
            <defs>
              <linearGradient id="hg2" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#166534" stopOpacity={0.25}/>
                <stop offset="95%" stopColor="#166534" stopOpacity={0.02}/>
              </linearGradient>
            </defs>
            <XAxis dataKey="d" tick={{fontSize:9}} axisLine={false} tickLine={false}/>
            <Tooltip formatter={v=>fmt(v)} contentStyle={{fontSize:11}}/>
            <Area type="monotone" dataKey="v" stroke="#166534" fill="url(#hg2)" strokeWidth={2} dot={false}/>
          </AreaChart>
        </ResponsiveContainer>
      ),
    },
    {
      id:"precios", icon:"💡", label:"Sugerir precios",
      color:"#fef3c7", border:"#d97706",
      badge:"4 productos analizados", badgeColor:"#d97706",
      chart: (
        <ResponsiveContainer width="100%" height={75}>
          <BarChart data={mockProductos.map(p=>({ name:p.nombre.split(" ")[0], margen:Math.round((p.precio-p.costo)/p.precio*100) }))}
            margin={{top:4,right:4,left:-30,bottom:0}}>
            <XAxis dataKey="name" tick={{fontSize:9}} axisLine={false} tickLine={false}/>
            <Tooltip formatter={v=>`${v}%`} contentStyle={{fontSize:11}}/>
            <Bar dataKey="margen" fill="#d97706" radius={[3,3,0,0]}/>
          </BarChart>
        </ResponsiveContainer>
      ),
    },
  ];

  return (
    <div>
      <h2 style={{ margin:"0 0 2px", fontSize:20, fontWeight:700 }}>Agente Financiero</h2>
      <p style={{ margin:"0 0 16px", color:"#6b7280", fontSize:13 }}>Dashboard · Resumen inteligente de tu negocio</p>
      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(130px,1fr))", gap:10, marginBottom:18 }}>
        {kpis.map((k,i) => (
          <div key={i} style={{ background:"#ffffff", borderRadius:"12px", padding:"12px 14px", boxShadow:"0 2px 12px rgba(0,0,0,0.08)", border:"1px solid #e5e7eb" }}>
            <div style={{ fontSize:10, color:"#6b7280", marginBottom:3 }}>{k.label}</div>
            <div style={{ fontSize:18, fontWeight:800 }}>{k.value}</div>
            <div style={{ fontSize:10, fontWeight:600, marginTop:2,
                          color: k.up===null ? "#0ea5e9" : k.up ? "#16a34a" : "#dc2626" }}>
              {k.delta}
            </div>
          </div>
        ))}
      </div>
      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(210px,1fr))", gap:14 }}>
        {dashCards.map(c => (
          <button key={c.id} onClick={()=>setActiveTab(c.id)} style={{
            background:c.color, border:`2px solid ${c.border}`, borderRadius:"12px",
            padding:"14px 14px 10px", cursor:"pointer", textAlign:"left",
            transition:"transform .15s, box-shadow .15s", display:"flex", flexDirection:"column", gap:6,
          }}
          onMouseEnter={e=>{ e.currentTarget.style.transform="translateY(-3px)"; e.currentTarget.style.boxShadow="0 8px 32px rgba(0,0,0,0.14)"; }}
          onMouseLeave={e=>{ e.currentTarget.style.transform="translateY(0)"; e.currentTarget.style.boxShadow="none"; }}>
            <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", flexWrap:"wrap", gap:4 }}>
              <div style={{ display:"flex", alignItems:"center", gap:6 }}>
                <span style={{ fontSize:20 }}>{c.icon}</span>
                <span style={{ fontWeight:700, fontSize:13, color:"#1f2937" }}>{c.label}</span>
              </div>
              <span style={{ fontSize:9, fontWeight:700, color:c.badgeColor,
                             background:"rgba(255,255,255,0.75)", borderRadius:10, padding:"2px 7px",
                             border:`1px solid ${c.badgeColor}`, whiteSpace:"nowrap" }}>
                {c.badge}
              </span>
            </div>
            <div style={{ pointerEvents:"none" }}>{c.chart}</div>
            <div style={{ fontSize:11, color:c.border, fontWeight:600, textAlign:"right" }}>Ver módulo →</div>
          </button>
        ))}
      </div>
    </div>
  );
}

/* ── GASTOS VIEW ── */
/*
function GastosView({ gastosFijos, setGastosFijos, gastosVariables, setGastosVariables }) {
  const [tipoGasto, setTipoGasto] = useState("fijo");
  const [form, setForm]           = useState({ concepto:"", monto:"", nota:"" });
  const [toast, setToast]         = useState("");

  const showToast = (msg) => { setToast(msg); setTimeout(()=>setToast(""),2500); };

  const agregar = () => {
    if (!form.concepto || !form.monto) { showToast("⚠️ Completa concepto y monto"); return; }
    const nuevo = { id:Date.now(), concepto:form.concepto, monto:parseFloat(form.monto), nota:form.nota };
    if (tipoGasto === "fijo") setGastosFijos(p=>[...p, nuevo]);
    else setGastosVariables(p=>[...p, nuevo]);
    setForm({ concepto:"", monto:"", nota:"" });
    showToast(`✅ Gasto ${tipoGasto === "fijo" ? "fijo" : "variable"} registrado`);
  };

  const eliminar = (id, tipo) => {
    if (tipo === "fijo") setGastosFijos(p=>p.filter(g=>g.id!==id));
    else setGastosVariables(p=>p.filter(g=>g.id!==id));
  };

  const totalFijos     = gastosFijos.reduce((s,g)=>s+g.monto,0);
  const totalVariables = gastosVariables.reduce((s,g)=>s+g.monto,0);
  const totalGeneral   = totalFijos + totalVariables;
  const chartData = [
    { name:"Gastos fijos",     total:totalFijos },
    { name:"Gastos variables", total:totalVariables },
  ];

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
      {toast && <Toast msg={toast} />}
      <SectionHeader icon="📝" title="Registro de Gastos"
        subtitle="Registra tus gastos fijos (siempre los pagas) y variables (cambian cada mes)." />
      <div style={{ background:"#e0f2fe", borderRadius:"8px", padding:12, fontSize:13, lineHeight:1.6, border:"1px solid #0ea5e9" }}>
        💡 <strong>¿Cuál es la diferencia?</strong><br/>
        <strong>Gastos fijos:</strong> Los pagas siempre, aunque no vendas nada (renta, luz, internet).<br/>
        <strong>Gastos variables:</strong> Cambian según cuánto vendas o compres (inventario, merma, bolsas).
      </div>
      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(300px,1fr))", gap:16 }}>
        <Card title="Registrar nuevo gasto">
          <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
            <div style={{ display:"flex", borderRadius:"8px", overflow:"hidden", border:"1.5px solid #7c3aed" }}>
              {["fijo","variable"].map(t => (
                <button key={t} onClick={()=>setTipoGasto(t)} style={{
                  flex:1, padding:"8px 0", border:"none", cursor:"pointer", fontWeight:600, fontSize:12,
                  background: tipoGasto===t ? "#7c3aed" : "transparent",
                  color: tipoGasto===t ? "#fff" : "#7c3aed",
                }}>
                  {t === "fijo" ? "🔒 Gasto fijo" : "📦 Gasto variable"}
                </button>
              ))}
            </div>
            <label style={labelStyle}>Concepto</label>
            <input value={form.concepto} onChange={e=>setForm(p=>({...p,concepto:e.target.value}))}
              placeholder={tipoGasto==="fijo" ? "Ej: Renta, Luz..." : "Ej: Inventario, Merma..."}
              style={inputStyle} />
            <label style={labelStyle}>Monto ($)</label>
            <input type="number" value={form.monto} onChange={e=>setForm(p=>({...p,monto:e.target.value}))}
              placeholder="0.00" style={inputStyle} />
            <label style={labelStyle}>Nota (opcional)</label>
            <input value={form.nota} onChange={e=>setForm(p=>({...p,nota:e.target.value}))}
              placeholder="Descripción breve..." style={inputStyle} />
            <button onClick={agregar} style={{ ...btnPrimary, marginTop:4 }}>Registrar gasto</button>
          </div>
        </Card>
        <Card title="Resumen de gastos del mes">
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:8, marginBottom:12 }}>
            {[
              { label:"Gastos fijos",     value:fmt(totalFijos),     color:"#dc2626" },
              { label:"Gastos variables", value:fmt(totalVariables), color:"#d97706" },
              { label:"Total general",    value:fmt(totalGeneral),   color:"#7c3aed" },
            ].map((k,i)=>(
              <div key={i} style={{ background:"#f8f7ff", borderRadius:8, padding:10, textAlign:"center" }}>
                <div style={{ fontSize:10, color:"#6b7280" }}>{k.label}</div>
                <div style={{ fontSize:15, fontWeight:700, color:k.color }}>{k.value}</div>
              </div>
            ))}
          </div>
          <ResponsiveContainer width="100%" height={140}>
            <BarChart data={chartData} margin={{ top:0, right:0, left:-20, bottom:0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="name" tick={{ fontSize:10 }} />
              <YAxis tick={{ fontSize:10 }} />
              <Tooltip formatter={v=>fmt(v)} />
              <Bar dataKey="total" radius={[4,4,0,0]} fill="#7c3aed" />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>
      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(300px,1fr))", gap:16 }}>
        {[
          { titulo:"🔒 Gastos Fijos", gastos:gastosFijos, tipo:"fijo", total:totalFijos, color:"#dc2626" },
          { titulo:"📦 Gastos Variables", gastos:gastosVariables, tipo:"variable", total:totalVariables, color:"#d97706" },
        ].map(({ titulo, gastos, tipo, total, color }) => (
          <Card key={tipo} title={titulo}>
            <div style={{ overflowX:"auto" }}>
              <table style={{ width:"100%", borderCollapse:"collapse", fontSize:13 }}>
                <thead>
                  <tr style={{ background:"#ede9fe" }}>
                    {["Concepto","Monto","Nota",""].map(h=>(
                      <th key={h} style={{ padding:"7px 10px", textAlign:"left", fontWeight:600, fontSize:11 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {gastos.map(g=>(
                    <tr key={g.id} style={{ borderBottom:"1px solid #e5e7eb" }}>
                      <td style={{ padding:"7px 10px", fontWeight:500 }}>{g.concepto}</td>
                      <td style={{ padding:"7px 10px", fontWeight:600, color }}>{fmt(g.monto)}</td>
                      <td style={{ padding:"7px 10px", color:"#6b7280", fontSize:11 }}>{g.nota||"—"}</td>
                      <td style={{ padding:"7px 10px" }}>
                        <button onClick={()=>eliminar(g.id, tipo)} style={{ background:"none", border:"none", color:"#dc2626", cursor:"pointer", fontSize:15 }}>🗑</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div style={{ textAlign:"right", padding:"8px 10px", fontWeight:700, fontSize:13, color }}>
                Total: {fmt(total)}
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

/* ── EQUILIBRIO VIEW ── */
/*
function EquilibrioView({ gastosFijos, gastosVariables }) {
  const [resico, setResico]         = useState(true);
  const [ingresosMes, setIngresosMes] = useState(51000);

  const totalFijos     = gastosFijos.reduce((s,g)=>s+g.monto,0);
  const totalVariables = gastosVariables.reduce((s,g)=>s+g.monto,0);
  const calidad        = gastosFijos.length + gastosVariables.length;
  const calidadLabel   = calidad >= 8
    ? { txt:"Alta ✅", color:"#16a34a", bg:"#dcfce7" }
    : calidad >= 4
    ? { txt:"Media ⚠️", color:"#d97706", bg:"#fef3c7" }
    : { txt:"Baja 🔴",  color:"#dc2626", bg:"#fee2e2" };

  const ratioVariable      = ingresosMes > 0 ? totalVariables / ingresosMes : 0;
  const margenContribucion = 1 - ratioVariable;
  const pe                 = margenContribucion > 0 ? totalFijos / margenContribucion : 0;
  const tasaResico         = ingresosMes <= 25000 ? 0.01 : ingresosMes <= 50000 ? 0.011 : 0.012;
  const impuestoResico     = resico ? ingresosMes * tasaResico : 0;

  const chartData = Array.from({ length: 10 }, (_, i) => {
    const v = (pe * 0.3) + i * (pe * 1.5 / 9);
    return { ventas:Math.round(v), gastosFijos:totalFijos, gastosVariables:Math.round(v*ratioVariable), ingreso:Math.round(v) };
  });
  const peX = chartData.reduce((prev,curr) =>
    Math.abs(curr.ventas - Math.round(pe)) < Math.abs(prev.ventas - Math.round(pe)) ? curr : prev
  ).ventas;

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
      <SectionHeader icon="⚖️" title="Punto de Equilibrio" subtitle="La venta mínima que necesitas para no perder dinero este mes." />
      <div style={{ background:calidadLabel.bg, borderRadius:"8px", padding:12, fontSize:13, border:`1px solid ${calidadLabel.color}`, lineHeight:1.6 }}>
        📊 <strong>Calidad de tu punto de equilibrio: <span style={{ color:calidadLabel.color }}>{calidadLabel.txt}</span></strong><br/>
        {calidad < 4 ? "Tienes pocos gastos registrados. Agrega más para mejorar la precisión."
          : calidad < 8 ? "Buen avance. Agrega más gastos variables para mejorar la precisión."
          : "¡Excelente! Tus datos están completos. Este punto de equilibrio es confiable."}
      </div>
      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(280px,1fr))", gap:16 }}>
        <Card title="Parámetros">
          <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
            <div>
              <label style={labelStyle}>Ingresos estimados del mes ($)</label>
              <input type="number" value={ingresosMes} onChange={e=>setIngresosMes(+e.target.value)} style={inputStyle} />
            </div>
            <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", background:"#f8f7ff", borderRadius:"8px", padding:"10px 14px", border:"1px solid #e5e7eb" }}>
              <div>
                <div style={{ fontWeight:600, fontSize:13 }}>Régimen RESICO</div>
                <div style={{ fontSize:11, color:"#6b7280" }}>{resico ? "Activo — ISR simplificado" : "Apagado"}</div>
              </div>
              <div onClick={()=>setResico(p=>!p)} style={{ width:44, height:24, borderRadius:12, cursor:"pointer", transition:"background .2s", background:resico?"#16a34a":"#e5e7eb", position:"relative", flexShrink:0 }}>
                <div style={{ position:"absolute", top:3, left:resico?22:3, width:18, height:18, borderRadius:"50%", background:"#fff", transition:"left .2s", boxShadow:"0 1px 4px rgba(0,0,0,0.2)" }} />
              </div>
            </div>
            <div style={{ background:"#ede9fe", borderRadius:"8px", padding:16, textAlign:"center" }}>
              <div style={{ fontSize:12, color:"#6b7280" }}>Tu punto de equilibrio es</div>
              <div style={{ fontSize:32, fontWeight:800, color:"#7c3aed" }}>{fmt(Math.round(pe))}</div>
              <div style={{ fontSize:12, color:"#6b7280" }}>al mes · {fmt(Math.round(pe/30))} al día</div>
            </div>
            {resico && (
              <div style={{ background:"#fef9c3", borderRadius:"8px", padding:12, fontSize:13, lineHeight:1.6, border:"1px solid #fde047" }}>
                🏛️ <strong>ISR RESICO estimado:</strong><br/>
                Tasa: <strong>{(tasaResico*100).toFixed(1)}%</strong> · Impuesto: <strong style={{ color:"#dc2626" }}>{fmt(Math.round(impuestoResico))}</strong>
              </div>
            )}
            <div style={{ background:"#dcfce7", borderRadius:"8px", padding:12, fontSize:13, lineHeight:1.6 }}>
              💬 Si vendes más de <strong>{fmt(Math.round(pe))}</strong> al mes, ya estás ganando.
            </div>
          </div>
        </Card>
        <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
          <Card title="📋 Desglose de gastos">
            <div style={{ fontSize:12, fontWeight:700, color:"#dc2626", marginBottom:6 }}>Gastos Fijos</div>
            {gastosFijos.map((g,i)=>(
              <div key={i} style={{ display:"flex", justifyContent:"space-between", fontSize:12, marginBottom:3 }}>
                <span>• {g.concepto}</span><strong style={{ color:"#dc2626" }}>{fmt(g.monto)}</strong>
              </div>
            ))}
            <div style={{ borderTop:"1px dashed #e5e7eb", marginTop:6, paddingTop:6, display:"flex", justifyContent:"space-between", fontWeight:700, fontSize:13 }}>
              <span>Subtotal fijos</span><span style={{ color:"#dc2626" }}>{fmt(totalFijos)}</span>
            </div>
            <div style={{ fontSize:12, fontWeight:700, color:"#d97706", marginTop:10, marginBottom:6 }}>Gastos Variables</div>
            {gastosVariables.map((g,i)=>(
              <div key={i} style={{ display:"flex", justifyContent:"space-between", fontSize:12, marginBottom:3 }}>
                <span>• {g.concepto}</span><strong style={{ color:"#d97706" }}>{fmt(g.monto)}</strong>
              </div>
            ))}
            <div style={{ borderTop:"1px dashed #e5e7eb", marginTop:6, paddingTop:6, display:"flex", justifyContent:"space-between", fontWeight:700, fontSize:13 }}>
              <span>Subtotal variables</span><span style={{ color:"#d97706" }}>{fmt(totalVariables)}</span>
            </div>
            <div style={{ borderTop:"2px solid #7c3aed", marginTop:8, paddingTop:8, display:"flex", justifyContent:"space-between", fontWeight:800, fontSize:14 }}>
              <span>TOTAL GASTOS</span>
              <span style={{ color:"#7c3aed" }}>{fmt(totalFijos + totalVariables + Math.round(impuestoResico))}</span>
            </div>
          </Card>
          <Card title="Gráfica de equilibrio">
            <ResponsiveContainer width="100%" height={200}>
              <ComposedChart data={chartData} margin={{ top:10, right:10, left:-10, bottom:0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="ventas" tick={{ fontSize:9 }} tickFormatter={v=>`$${(v/1000).toFixed(0)}k`} />
                <YAxis tick={{ fontSize:9 }} tickFormatter={v=>`$${(v/1000).toFixed(0)}k`} />
                <Tooltip formatter={v=>fmt(v)} />
                <Legend wrapperStyle={{ fontSize:10 }} />
                <Area type="monotone" dataKey="ingreso" fill="#ede9fe" stroke="#7c3aed" strokeWidth={2} name="Ingresos" />
                <Line type="monotone" dataKey="gastosFijos" stroke="#dc2626" strokeWidth={2} dot={false} name="Gastos fijos" strokeDasharray="5 5" />
                <Line type="monotone" dataKey="gastosVariables" stroke="#d97706" strokeWidth={2} dot={false} name="Gastos variables" />
                <ReferenceLine x={peX} stroke="#16a34a" strokeWidth={3} label={{ value:"PE ✓", fill:"#16a34a", fontSize:11, fontWeight:"bold" }} />
              </ComposedChart>
            </ResponsiveContainer>
            <div style={{ fontSize:11, color:"#16a34a", textAlign:"center", marginTop:4, fontWeight:600 }}>
              🟢 Punto de equilibrio: {fmt(Math.round(pe))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

/* ── PRECIOS VIEW ── */
/*
function PreciosView() {
  const [producto, setProducto]     = useState({ nombre:"Leche Lala 1L", costo:18, margenDeseado:25 });
  const [estado, setEstado]         = useState(null);
  const [precioAjuste, setPrecioAjuste] = useState("");

  const precioSugerido   = Math.ceil(producto.costo / (1 - producto.margenDeseado / 100));
  const gananciaUnitaria = precioSugerido - producto.costo;
  const margenFinal      = precioAjuste
    ? (((precioAjuste - producto.costo) / precioAjuste) * 100).toFixed(1)
    : producto.margenDeseado.toFixed(1);

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
      <SectionHeader icon="💡" title="Sugerir Precios" subtitle="El precio sugerido se calcula con una fórmula de margen sobre costo. Tú siempre decides el precio final." />
      <div style={{ background:"#e0f2fe", borderRadius:"8px", padding:12, fontSize:13, lineHeight:1.7, border:"1px solid #0ea5e9" }}>
        🧮 <strong>¿Cómo se calcula?</strong> Precio = Costo ÷ (1 − Margen%)<br/>
        Ejemplo: $18 ÷ 0.75 = <strong>$24</strong><br/>
        <span style={{ color:"#6b7280", fontSize:11 }}>⚠️ No considera precios de competencia. Es un punto de partida basado en tus costos.</span>
      </div>
      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(280px,1fr))", gap:16 }}>
        <Card title="Datos del producto">
          <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
            <label style={labelStyle}>Nombre del producto</label>
            <input value={producto.nombre} onChange={e=>setProducto(p=>({...p,nombre:e.target.value}))} style={inputStyle} />
            <label style={labelStyle}>Costo de compra ($)</label>
            <input type="number" value={producto.costo} onChange={e=>setProducto(p=>({...p,costo:+e.target.value}))} style={inputStyle} />
            <label style={labelStyle}>Margen de ganancia deseado (%)</label>
            <div style={{ display:"flex", alignItems:"center", gap:10 }}>
              <input type="range" min={5} max={60} value={producto.margenDeseado}
                onChange={e=>setProducto(p=>({...p,margenDeseado:+e.target.value}))}
                style={{ flex:1, accentColor:"#7c3aed" }} />
              <span style={{ fontWeight:700, color:"#7c3aed", minWidth:36 }}>{producto.margenDeseado}%</span>
            </div>
            <div style={{ background:"#f8f7ff", borderRadius:8, padding:10, fontSize:12, lineHeight:1.6 }}>
              Con {producto.margenDeseado}% de margen, de cada {fmt(precioSugerido)} cobrado,
              <strong style={{ color:"#16a34a" }}> {fmt(gananciaUnitaria)} es tu ganancia</strong>.
            </div>
          </div>
        </Card>
        <Card title="Precio sugerido">
          <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:8 }}>
              {[
                { label:"Costo de compra",  value:fmt(producto.costo),          color:"#1f2937" },
                { label:"Ganancia unitaria", value:fmt(gananciaUnitaria),        color:"#16a34a" },
                { label:"Precio sugerido",  value:fmt(precioSugerido),           color:"#7c3aed" },
                { label:"Margen aplicado",  value:`${producto.margenDeseado}%`,  color:"#d97706" },
              ].map((item,i)=>(
                <div key={i} style={{ background:"#f8f7ff", borderRadius:8, padding:10, textAlign:"center" }}>
                  <div style={{ fontSize:10, color:"#6b7280" }}>{item.label}</div>
                  <div style={{ fontSize:18, fontWeight:700, color:item.color }}>{item.value}</div>
                </div>
              ))}
            </div>
            <div style={{ background:"#f3e8ff", borderRadius:8, padding:12, fontSize:13, lineHeight:1.6 }}>
              🧮 {fmt(producto.costo)} ÷ (1 − {producto.margenDeseado/100}) = <strong>{fmt(precioSugerido)}</strong>
            </div>
            {!estado && (
              <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                <div style={{ display:"flex", gap:8 }}>
                  <button onClick={()=>setEstado("aceptado")} style={{ ...btnPrimary, flex:1 }}>✅ Aceptar</button>
                  <button onClick={()=>setEstado("rechazado")} style={{ ...btnDanger, flex:1 }}>❌ Rechazar</button>
                </div>
                <button onClick={()=>setEstado("ajustado")} style={btnSecondary}>✏️ Ajustar manualmente</button>
              </div>
            )}
            {estado === "ajustado" && (
              <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                <label style={labelStyle}>Tu precio de venta ($)</label>
                <input type="number" value={precioAjuste} onChange={e=>setPrecioAjuste(e.target.value)} placeholder={precioSugerido} style={inputStyle} />
                {precioAjuste && (
                  <div style={{ background:+margenFinal<10?"#fee2e2":"#dcfce7", borderRadius:8, padding:10, fontSize:12 }}>
                    {+margenFinal<10 ? `⚠️ Margen de ${margenFinal}%. Puede ser insuficiente.` : `✅ Margen de ${margenFinal}%. ¡Bien!`}
                  </div>
                )}
                <button onClick={()=>setEstado("aceptado")} style={btnPrimary}>Confirmar precio</button>
              </div>
            )}
            {estado === "aceptado" && (
              <div style={{ background:"#dcfce7", borderRadius:8, padding:12, fontSize:13, textAlign:"center" }}>
                ✅ Precio <strong>{fmt(precioAjuste||precioSugerido)}</strong> guardado para <strong>{producto.nombre}</strong>
                <br/><button onClick={()=>{setEstado(null);setPrecioAjuste("");}} style={{ ...btnSecondary, marginTop:8, fontSize:11 }}>Analizar otro</button>
              </div>
            )}
            {estado === "rechazado" && (
              <div style={{ background:"#fef3c7", borderRadius:8, padding:12, fontSize:13, textAlign:"center" }}>
                👍 Entendido. Tú conoces mejor tu mercado.
                <br/><button onClick={()=>setEstado(null)} style={{ ...btnSecondary, marginTop:8, fontSize:11 }}>Volver</button>
              </div>
            )}
          </div>
        </Card>
      </div>
      <Card title="Comparativa de productos — precios sugeridos (25% margen)">
        <div style={{ overflowX:"auto" }}>
          <table style={{ width:"100%", borderCollapse:"collapse", fontSize:13 }}>
            <thead>
              <tr style={{ background:"#ede9fe" }}>
                {["Producto","Costo","Precio actual","Precio sugerido","Ganancia","Margen actual"].map(h=>(
                  <th key={h} style={{ padding:"8px 12px", textAlign:"left", fontSize:11, fontWeight:600 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {mockProductos.map((p,i)=>{
                const pSug = Math.ceil(p.costo / 0.75);
                const ganancia = pSug - p.costo;
                const mActual = ((p.precio - p.costo) / p.precio * 100).toFixed(0);
                return (
                  <tr key={i} style={{ borderBottom:"1px solid #e5e7eb" }}>
                    <td style={{ padding:"8px 12px", fontWeight:500 }}>{p.nombre}</td>
                    <td style={{ padding:"8px 12px" }}>{fmt(p.costo)}</td>
                    <td style={{ padding:"8px 12px" }}>{fmt(p.precio)}</td>
                    <td style={{ padding:"8px 12px", color:"#7c3aed", fontWeight:600 }}>{fmt(pSug)}</td>
                    <td style={{ padding:"8px 12px", color:"#16a34a", fontWeight:600 }}>{fmt(ganancia)}</td>
                    <td style={{ padding:"8px 12px" }}>
                      <span style={{ ...badge, background:+mActual<15?"#fee2e2":"#dcfce7", color:+mActual<15?"#dc2626":"#16a34a" }}>{mActual}%</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

/* ── FORECAST VIEW ── */
/*
function ForecastView() {
  const [generando, setGenerando]   = useState(false);
  const [progreso, setProgreso]     = useState([]);
  const [catActual, setCatActual]   = useState(-1);
  const [listo, setListo]           = useState(false);
  const [resultados, setResultados] = useState([]);
  const [confianza, setConfianza]   = useState(null);

  const generarPronostico = () => {
    setGenerando(true); setProgreso([]); setResultados([]); setCatActual(-1); setListo(false); setConfianza(null);
    let catIdx = 0, prodIdx = 0;
    const res = [];
    const tick = () => {
      if (catIdx >= categoriasForecast.length) {
        const conf = Math.floor(Math.random()*15)+72;
        setConfianza(conf); setListo(true); setGenerando(false); setResultados(res); return;
      }
      const cat = categoriasForecast[catIdx];
      const prod = cat.productos[prodIdx];
      const uds = Math.floor(Math.random()*60)+10;
      res.push({ cat:cat.cat, prod, uds });
      setProgreso(p=>[...p,{ cat:cat.cat, prod, uds }]);
      setCatActual(catIdx);
      prodIdx++;
      if (prodIdx >= cat.productos.length) { catIdx++; prodIdx=0; }
      setTimeout(tick, 320);
    };
    setTimeout(tick, 500);
  };

  const totalUds = resultados.reduce((s,r)=>s+r.uds,0);

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
      <SectionHeader icon="📈" title="Pronóstico de Ventas" subtitle="Generado por un modelo de Machine Learning externo entrenado con tu historial de ventas." />
      <div style={{ background:"#e0f2fe", borderRadius:"8px", padding:12, fontSize:13, lineHeight:1.7, border:"1px solid #0ea5e9" }}>
        🤖 <strong>¿Cómo funciona?</strong> Un modelo de <strong>Machine Learning</strong> analiza tu historial de <strong>24 semanas</strong> para estimar cuántas unidades venderás esta semana. <strong>El AVI te ayuda a interpretar los resultados.</strong>
      </div>
      <Card title="Generar nuevo pronóstico semanal">
        <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
          <button onClick={generarPronostico} disabled={generando} style={{ ...btnPrimary, background:generando?"#a78bfa":"#7c3aed", cursor:generando?"not-allowed":"pointer", display:"flex", alignItems:"center", justifyContent:"center", gap:8, fontSize:14, padding:"12px 16px" }}>
            {generando ? "⏳ Consultando modelo ML..." : "🚀 Generar pronóstico semanal"}
          </button>
          {(generando || listo) && (
            <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
              <div style={{ fontWeight:700, fontSize:13, color:"#7c3aed" }}>
                {generando ? "📡 Procesando historial de 24 semanas..." : "✅ Pronóstico completado"}
              </div>
              {categoriasForecast.map((cat,ci) => {
                const catItems = progreso.filter(p=>p.cat===cat.cat);
                if (catItems.length===0 && ci>catActual) return null;
                return (
                  <div key={ci} style={{ background:"#ffffff", borderRadius:8, border:"1px solid #e5e7eb", overflow:"hidden" }}>
                    <div style={{ background:"#ede9fe", padding:"6px 12px", fontWeight:700, fontSize:12, color:"#7c3aed", display:"flex", alignItems:"center", gap:6 }}>
                      {catItems.length>=cat.productos.length?"✅":"⏳"} {cat.cat}
                    </div>
                    {catItems.map((item,ii)=>(
                      <div key={ii} style={{ display:"flex", justifyContent:"space-between", alignItems:"center", padding:"6px 14px", borderTop:"1px solid #e5e7eb", fontSize:13 }}>
                        <span>• {item.prod}</span>
                        <span style={{ background:"#dcfce7", color:"#16a34a", borderRadius:12, padding:"2px 10px", fontWeight:700, fontSize:12 }}>{item.uds} uds</span>
                      </div>
                    ))}
                  </div>
                );
              })}
            </div>
          )}
          {listo && confianza !== null && (
            <div style={{ display:"flex", flexDirection:"column", gap:10, marginTop:4 }}>
              <div style={{ background:"#ffffff", borderRadius:"8px", padding:14, border:"1px solid #e5e7eb" }}>
                <div style={{ fontWeight:700, fontSize:13, marginBottom:8 }}>📊 Nivel de confianza del modelo</div>
                <div style={{ display:"flex", alignItems:"center", gap:12 }}>
                  <div style={{ flex:1, background:"#e5e7eb", borderRadius:20, height:12, overflow:"hidden" }}>
                    <div style={{ width:`${confianza}%`, height:"100%", background:"linear-gradient(90deg,#7c3aed,#16a34a)", borderRadius:20, transition:"width 1s ease" }} />
                  </div>
                  <span style={{ fontWeight:800, fontSize:20, color:"#7c3aed", minWidth:48 }}>{confianza}%</span>
                </div>
                <div style={{ fontSize:11, color:"#6b7280", marginTop:6 }}>
                  {confianza>=80?"✅ Confianza alta.":confianza>=70?"⚠️ Confianza media.":"🔴 Confianza baja."}
                </div>
              </div>
              <div style={{ background:"#f3e8ff", borderRadius:"8px", padding:12, fontSize:13, lineHeight:1.7, border:"1px solid #c4b5fd" }}>
                🤖 <strong>AVI interpreta:</strong> Estimación de <strong>{totalUds} unidades</strong> en {resultados.length} productos esta semana. Asegura stock antes del viernes.
              </div>
              <div style={{ background:"#dcfce7", borderRadius:"8px", padding:12, fontSize:13, lineHeight:1.6 }}>
                📦 <strong>Total estimado: {totalUds} unidades</strong> · Confianza: {confianza}%
              </div>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}

/* ── REPORTES VIEW ── */
/*
function ReportesView() {
  const [periodo, setPeriodo] = useState("6m");
  const data           = periodo==="3m" ? reporteData.slice(-3) : reporteData;
  const totalIngresos  = data.reduce((s,d)=>s+d.ingresos,0);
  const totalEgresos   = data.reduce((s,d)=>s+d.egresos,0);
  const totalUtilidad  = data.reduce((s,d)=>s+d.utilidad,0);
  const margenProm     = ((totalUtilidad/totalIngresos)*100).toFixed(1);

  const alertas = [
    { tipo:"danger",  msg:"🔴 Abril: egresos subieron 6% sin aumento en ventas." },
    { tipo:"warning", msg:"🟡 Leche Lala: baja rotación. Considera una promoción." },
    { tipo:"info",    msg:"🔵 Mayo y Junio son tus mejores meses. Aumenta stock." },
    { tipo:"success", msg:"🟢 Junio: mejor utilidad del semestre ($17,000). ¡Bien!" },
  ];
  const colorMap = {
    danger:  { bg:"#fee2e2", color:"#dc2626" },
    warning: { bg:"#fef3c7", color:"#d97706" },
    info:    { bg:"#e0f2fe", color:"#0ea5e9" },
    success: { bg:"#dcfce7", color:"#16a34a" },
  };

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", flexWrap:"wrap", gap:8 }}>
        <SectionHeader icon="📊" title="Reportes Financieros" subtitle="Resumen visual de ingresos, egresos y utilidades." />
        <div style={{ display:"flex", gap:6 }}>
          {["3m","6m"].map(p=>(
            <button key={p} onClick={()=>setPeriodo(p)} style={{ padding:"6px 14px", borderRadius:20, border:`2px solid ${periodo===p?"#7c3aed":"#e5e7eb"}`, background:periodo===p?"#7c3aed":"#ffffff", color:periodo===p?"#fff":"#1f2937", fontWeight:600, fontSize:12, cursor:"pointer" }}>
              {p==="3m"?"3 meses":"6 meses"}
            </button>
          ))}
        </div>
      </div>
      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(140px,1fr))", gap:12 }}>
        {[
          { label:"Ingresos totales", value:fmt(totalIngresos), color:"#7c3aed" },
          { label:"Egresos totales",  value:fmt(totalEgresos),  color:"#dc2626" },
          { label:"Utilidad neta",    value:fmt(totalUtilidad), color:"#16a34a" },
          { label:"Margen promedio",  value:`${margenProm}%`,   color:"#d97706" },
        ].map((k,i)=>(
          <div key={i} style={{ background:"#ffffff", borderRadius:"12px", padding:14, boxShadow:"0 2px 12px rgba(0,0,0,0.08)", textAlign:"center" }}>
            <div style={{ fontSize:11, color:"#6b7280", marginBottom:4 }}>{k.label}</div>
            <div style={{ fontSize:18, fontWeight:700, color:k.color }}>{k.value}</div>
          </div>
        ))}
      </div>
      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(300px,1fr))", gap:16 }}>
        <Card title="Ingresos vs Egresos">
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={data} margin={{ top:5, right:5, left:-15, bottom:0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="mes" tick={{ fontSize:11 }} />
              <YAxis tick={{ fontSize:9 }} tickFormatter={v=>`$${(v/1000).toFixed(0)}k`} />
              <Tooltip formatter={v=>fmt(v)} />
              <Legend wrapperStyle={{ fontSize:11 }} />
              <Bar dataKey="ingresos" fill="#7c3aed" name="Ingresos" radius={[3,3,0,0]} />
              <Bar dataKey="egresos"  fill="#dc2626" name="Egresos"  radius={[3,3,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
        <Card title="Utilidad neta mensual">
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={data} margin={{ top:5, right:5, left:-15, bottom:0 }}>
              <defs>
                <linearGradient id="utilGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#16a34a" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#16a34a" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="mes" tick={{ fontSize:11 }} />
              <YAxis tick={{ fontSize:9 }} tickFormatter={v=>`$${(v/1000).toFixed(0)}k`} />
              <Tooltip formatter={v=>fmt(v)} />
              <Area type="monotone" dataKey="utilidad" stroke="#16a34a" fill="url(#utilGrad)" strokeWidth={2} name="Utilidad" dot={{ r:4 }} />
            </AreaChart>
          </ResponsiveContainer>
        </Card>
      </div>
      <Card title="🔔 Alertas y sugerencias del AVI">
        <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
          {alertas.map((a,i)=>(
            <div key={i} style={{ background:colorMap[a.tipo].bg, borderRadius:8, padding:"10px 14px", fontSize:13, lineHeight:1.5, borderLeft:`4px solid ${colorMap[a.tipo].color}` }}>
              {a.msg}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

/* ══════════════════════════════════════════
   APP PRINCIPAL
══════════════════════════════════════════ */
/*
function App() {
  const [activeTab, setActiveTab]   = useState("home");
  const [aviOpen, setAviOpen]       = useState(false);
  const [aviInput, setAviInput]     = useState("");
  const [aviChat, setAviChat]       = useState([{ from:"avi", text:aviMessages.home }]);
  const [gastosFijos, setGastosFijos]         = useState(gastosIniciales.fijos);
  const [gastosVariables, setGastosVariables] = useState(gastosIniciales.variables);
  const chatRef = useRef(null);

  useEffect(() => {
    const msg = aviMessages[activeTab] || aviMessages.home;
    setAviChat(p => {
      if (p[p.length-1]?.text === msg) return p;
      return [...p, { from:"avi", text:msg }];
    });
  }, [activeTab]);

  useEffect(() => {
    if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight;
  }, [aviChat]);

  const sendAvi = () => {
    if (!aviInput.trim()) return;
    const userMsg = aviInput.trim();
    setAviChat(p=>[...p,{ from:"user", text:userMsg }]);
    setAviInput("");
    setTimeout(()=>setAviChat(p=>[...p,{ from:"avi", text:"Entendido 👍 Déjame analizar eso con tus datos." }]),800);
  };

  const tabs = [
    { id:"home",       label:"Inicio" },
    { id:"gastos",     label:"Registrar gastos" },
    { id:"equilibrio", label:"Punto de equilibrio" },
    { id:"precios",    label:"Sugerir precios" },
    { id:"forecast",   label:"Pronóstico de ventas" },
    { id:"reportes",   label:"Reportes financieros" },
  ];

  return (
    <div style={{ fontFamily:"'Segoe UI',sans-serif", background:"#f8f7ff", minHeight:"100vh", color:"#1f2937" }}>
      {/* NAV *//*}
      <nav style={{ background:"#ffffff", borderBottom:"1px solid #e5e7eb", display:"flex", gap:4, padding:"0 16px", overflowX:"auto", boxShadow:"0 2px 12px rgba(0,0,0,0.08)" }}>
        {[
          { id:"modulo-venta", label:"Módulo de venta" },
          { id:"inventario",   label:"Auxiliar de inventario" },
          { id:"financiero",   label:"Agente financiero", active:true },
        ].map(t=>(
          <button key={t.id} style={{ padding:"12px 18px", border:"none", cursor:"pointer", fontWeight:600, fontSize:13, whiteSpace:"nowrap", background:"transparent", color:t.active?"#2563eb":"#6b7280", borderBottom:t.active?"3px solid #2563eb":"3px solid transparent", borderRadius:"8px 8px 0 0" }}>{t.label}</button>
        ))}
      </nav>

      <div style={{ display:"flex", height:"calc(100vh - 49px)", overflow:"hidden" }}>
        {/* AVI SIDEBAR }
        <aside style={{ width:220, minWidth:220, background:"linear-gradient(160deg,#7c3aed 0%,#5b21b6 100%)", display:"flex", flexDirection:"column", padding:16, gap:12, boxShadow:"2px 0 12px rgba(0,0,0,0.1)" }}>
          <div style={{ textAlign:"center", color:"#fff" }}>
            <div style={{ fontSize:40, marginBottom:4 }}>🤖</div>
            <div style={{ fontWeight:700, fontSize:14 }}>Asistente Virtual</div>
            <div style={{ fontWeight:700, fontSize:14 }}>Inteligente</div>
          </div>
          <div style={{ background:"rgba(255,255,255,0.15)", borderRadius:"8px", padding:10, color:"#fff", fontSize:12, lineHeight:1.5, flex:1, overflowY:"auto" }} ref={chatRef}>
            {aviChat.map((m,i)=>(
              <div key={i} style={{ marginBottom:8, textAlign:m.from==="user"?"right":"left" }}>
                <span style={{ display:"inline-block", padding:"6px 10px", borderRadius:m.from==="user"?"12px 12px 0 12px":"12px 12px 12px 0", background:m.from==="user"?"rgba(255,255,255,0.3)":"rgba(255,255,255,0.15)", fontSize:11, maxWidth:"90%" }}>{m.text}</span>
              </div>
            ))}
          </div>
          <div style={{ display:"flex", gap:6 }}>
            <input value={aviInput} onChange={e=>setAviInput(e.target.value)} onKeyDown={e=>e.key==="Enter"&&sendAvi()} placeholder="Escribe aquí..."
              style={{ flex:1, padding:"8px 10px", borderRadius:"8px", border:"none", fontSize:12, outline:"none" }} />
            <button onClick={sendAvi} style={{ background:"#f59e0b", border:"none", borderRadius:"8px", color:"#fff", fontWeight:700, padding:"0 10px", cursor:"pointer", fontSize:14 }}>➤</button>
          </div>
        </aside>

        {/* MAIN CONTENT /*}
        <main style={{ flex:1, overflowY:"auto", padding:20, display:"flex", flexDirection:"column", gap:16 }}>
          <div style={{ display:"flex", gap:8, flexWrap:"wrap" }}>
            {tabs.map(t=>(
              <button key={t.id} onClick={()=>setActiveTab(t.id)} style={{ padding:"8px 16px", borderRadius:20, border:`2px solid ${activeTab===t.id?"#7c3aed":"#e5e7eb"}`, background:activeTab===t.id?"#7c3aed":"#ffffff", color:activeTab===t.id?"#fff":"#1f2937", fontWeight:600, fontSize:12, cursor:"pointer", transition:"all .2s" }}>{t.label}</button>
            ))}
          </div>
          {activeTab==="home"       && <HomeView setActiveTab={setActiveTab} />}
          {activeTab==="gastos"     && <GastosView gastosFijos={gastosFijos} setGastosFijos={setGastosFijos} gastosVariables={gastosVariables} setGastosVariables={setGastosVariables} />}
          {activeTab==="equilibrio" && <EquilibrioView gastosFijos={gastosFijos} gastosVariables={gastosVariables} />}
          {activeTab==="precios"    && <PreciosView />}
          {activeTab==="forecast"   && <ForecastView />}
          {activeTab==="reportes"   && <ReportesView />}
        </main>
      </div>

      <style>{`* { box-sizing:border-box; } ::-webkit-scrollbar { width:6px; height:6px; } ::-webkit-scrollbar-thumb { background:#c4b5fd; border-radius:3px; }`}</style>
    </div>
  );
}

*/
export default App
