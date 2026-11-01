import { useState, type ReactNode } from 'react';
import { Link, useLocation } from 'wouter';
import { Compass, Map, Bookmark, BookOpen, UserRound, Plus, Menu, X, CircleHelp, Leaf } from 'lucide-react';
import type { AuthUser } from '../lib/auth';
export function Shell({children,user,authLoading,onLogout}:{children:ReactNode;user:AuthUser|null;authLoading:boolean;onLogout:()=>void}) {
 const [loc]=useLocation(); const [open,setOpen]=useState(false);
 const nav=[['/','Today',Compass],['/explore','Explore',Map],['/trips','My trips',Leaf],['/saved','Saved places',Bookmark],['/guides','Field notes',BookOpen],['/profile','Profile',UserRound]] as const;
 const auth=loc.startsWith('/auth/');
 if(auth)return <main>{children}</main>;
 return <div className="app-shell">
  <aside className={`sidebar ${open?'sidebar-open':''}`}><Link href="/" className="brand"><span className="brand-mark"><Compass size={21}/></span><span>treavue<small>TRAVEL, THOUGHTFULLY</small></span></Link><div className="side-label">YOUR SPACE</div><nav>{nav.map(([href,label,Icon])=><Link href={href} key={href} onClick={()=>setOpen(false)} className={`nav-link ${loc===href||(href!=='/'&&loc.startsWith(href))?'active':''}`} data-testid={`nav-${label.toLowerCase().replaceAll(' ','-')}`}><Icon size={18}/><span>{label}</span></Link>)}</nav><Link href="/plan" className="plan-button" data-testid="link-plan-trip"><Plus size={17}/> Plan a trip</Link><div className="sidebar-bottom">{user&&<div className="storage-tag"><span className="storage-dot"/><div><strong>Account storage</strong><small>Private trips</small></div></div>}<div className="sidebar-help"><CircleHelp size={16}/> Your plans stay private</div></div></aside>
  {open&&<button className="mobile-scrim" onClick={()=>setOpen(false)} aria-label="Close navigation"/>}
  <div className="main-column"><header className="topbar"><button className="mobile-menu" onClick={()=>setOpen(!open)} aria-label="Toggle navigation">{open?<X/>:<Menu/>}</button><div className="topbar-date">A little more room to wander.</div><div className="topbar-right">{authLoading?<span className="account-pill">Restoring session…</span>:user?<><span className="account-pill">{user.email||'Signed in'}</span><button className="avatar" onClick={onLogout} aria-label="Sign out">Out</button></>:<Link href="/auth/sign-in" className="avatar" aria-label="Sign in">Sign in</Link>}</div></header><main className="main-content">{children}</main><footer className="app-footer"><span>Treavue · your personal travel notebook</span><span>{user?'Your trips are tied to your account.':'Your plans can stay in this browser or sync to your account.'}</span></footer></div>
 </div>
}
