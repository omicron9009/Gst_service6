const API="http://localhost:8000"

let users=[]

function addUser(gstin){

if(users.includes(gstin)) return

users.push(gstin)

const opt=document.createElement("option")
opt.value=gstin
opt.text=gstin

document.getElementById("gstinSelect").appendChild(opt)

renderUsers()
}

function renderUsers(){

const list=document.getElementById("userList")
list.innerHTML=""

users.forEach(gstin=>{

const div=document.createElement("div")

div.innerHTML=`
<b>${gstin}</b>
<button onclick="refreshSession('${gstin}')">Refresh</button>
<button onclick="openDashboard('${gstin}')">Open</button>
`

list.appendChild(div)

})
}


async function checkSession(){

const gstin=document.getElementById("gstinCheck").value

const res=await fetch(API+"/auth/session/"+gstin)
const data=await res.json()

if(data.active){

addUser(gstin)
refreshSession(gstin)

}else{

alert("No active session")

}

}


async function generateOTP(){

const username=document.getElementById("username").value
const gstin=document.getElementById("gstin").value

await fetch(API+"/auth/generate-otp",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({username,gstin})
})

alert("OTP sent")

}


async function verifyOTP(){

const username=document.getElementById("username").value
const gstin=document.getElementById("gstin").value
const otp=document.getElementById("otp").value

const res=await fetch(API+"/auth/verify-otp",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({username,gstin,otp})
})

const data=await res.json()

if(data.success){

addUser(gstin)

}else{

alert("Login failed")

}

}


async function refreshSession(gstin){

await fetch(API+"/auth/refresh",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({gstin})
})

}


function openDashboard(gstin){

document.getElementById("gstinSelect").value=gstin
loadDashboard()

}


async function loadDashboard(){

const gstin=document.getElementById("gstinSelect").value
const year=document.getElementById("year").value
const month=document.getElementById("month").value

loadSummary(gstin,year,month)
loadB2B(gstin,year,month)
loadB2CS(gstin,year,month)
loadHSN(gstin,year,month)
loadNil(gstin,year,month)
loadCDNR(gstin,year,month)
loadDocs(gstin,year,month)

}



async function loadSummary(gstin,y,m){

const res=await fetch(`${API}/gstr1/b2b/${gstin}/${y}/${m}`)
const data=await res.json()

const s=data.summary

const cards=document.getElementById("summaryCards")

cards.innerHTML=`

<div class="card">Invoices<br><b>${s.total_invoices}</b></div>
<div class="card">Taxable<br><b>${s.total_taxable_value}</b></div>
<div class="card">CGST<br><b>${s.total_cgst}</b></div>
<div class="card">SGST<br><b>${s.total_sgst}</b></div>
<div class="card">IGST<br><b>${s.total_igst}</b></div>

`

}



async function loadB2B(gstin,y,m){

const res=await fetch(`${API}/gstr1/b2b/${gstin}/${y}/${m}`)
const data=await res.json()

const rows=data.invoices

renderTable("b2bTable",rows)

}



async function loadB2CS(gstin,y,m){

const res=await fetch(`${API}/gstr1/b2cs/${gstin}/${y}/${m}`)
const data=await res.json()

renderTable("b2csTable",data.records)

}


async function loadHSN(gstin,y,m){

const res=await fetch(`${API}/gstr1/hsn/${gstin}/${y}/${m}`)
const data=await res.json()

renderTable("hsnTable",data.records)

}


async function loadNil(gstin,y,m){

const res=await fetch(`${API}/gstr1/nil/${gstin}/${y}/${m}`)
const data=await res.json()

renderTable("nilTable",data.records)

}


async function loadCDNR(gstin,y,m){

const res=await fetch(`${API}/gstr1/cdnr/${gstin}/${y}/${m}`)
const data=await res.json()

renderTable("cdnrTable",data.records)

}


async function loadDocs(gstin,y,m){

const res=await fetch(`${API}/gstr1/doc-issue/${gstin}/${y}/${m}`)
const data=await res.json()

renderTable("docTable",data.records)

}


function renderTable(id,data){

const table=document.getElementById(id)

if(!data || data.length===0){

table.innerHTML="No Data"
return

}

const headers=Object.keys(data[0])

let html="<tr>"

headers.forEach(h=>{
html+=`<th>${h}</th>`
})

html+="</tr>"

data.forEach(row=>{

html+="<tr>"

headers.forEach(h=>{
html+=`<td>${row[h] ?? ""}</td>`
})

html+="</tr>"

})

table.innerHTML=html

}