// Literal sequential arithmetic used by Pine; no fast-math or reassociation.
#include <algorithm>
#include <cmath>
#include <vector>
extern "C" {
void vp_levels(const double* v, int n, int key, double row, double target, double* out) {
  int p=0; for(int i=1;i<n;++i) if(v[i]>v[p]) p=i;
  int lo=p,hi=p; double cum=v[p];
  while(cum<target && (lo>0 || hi<n-1)) {
    double b=lo>0?v[lo-1]:-1, a=hi<n-1?v[hi+1]:-1;
    if(a>=b) cum+=v[++hi]; else cum+=v[--lo];
  }
  out[0]=(key+hi)*row;out[1]=(key+p)*row;out[2]=(key+lo)*row;
}
int hvn_build(const double* h,const double* l,const double* v,int size,
             double row,int smooth,double pct,int win,double prom,double expand,
             double width,double* out,double* meta) {
  double base=l[0],top=h[0];
  for(int i=1;i<size;++i){base=std::min(base,l[i]);top=std::max(top,h[i]);}
  int n=std::ceil((top-base)/row)+1;
  if(n>3000){row=std::ceil(((top-base)/2999)/.25)*.25;n=std::ceil((top-base)/row)+1;}
  std::vector<double> mass(n,0),s(n,0);
  double input=0;
  for(int i=0;i<size;++i){
    int a=std::floor((l[i]-base)/row),b=std::min(n-1,int(std::floor((h[i]-base)/row)));
    double volume=std::isfinite(v[i])?v[i]:0,share=volume/(b-a+1);input+=volume;
    for(int q=a;q<=b;++q)mass[q]+=share;
  }
  double vmax=0,total=0;
  for(int r=0;r<n;++r){
    int a=std::max(0,r-smooth/2),b=std::min(n-1,r+smooth/2);
    double sum=0;for(int q=a;q<=b;++q)sum+=mass[q];
    s[r]=sum/(b-a+1);vmax=std::max(vmax,s[r]);total+=mass[r];
  }
  int count=0;
  if(vmax>0)for(int r=0;r<n;++r){
    double value=s[r];if(value<vmax*(pct*100.0)/100.0)continue;
    bool peak=true;
    for(int q=std::max(0,r-win);q<=std::min(n-1,r+win);++q)
      if(q!=r && (s[q]>value || (s[q]==value && q<r))){peak=false;break;}
    if(!peak)continue;
    double lt=value,rt=value;
    for(int q=r-1;q>=0;--q){if(s[q]>value)break;lt=std::min(lt,s[q]);}
    for(int q=r+1;q<n;++q){if(s[q]>value)break;rt=std::min(rt,s[q]);}
    double prominence=value-std::max(lt,rt);if(prominence<value*(prom*100.0)/100.0)continue;
    double floor=value-prominence*(expand*100.0)/100.0;int a=r,b=r;
    while(a>0 && s[a-1]>=floor)--a;while(b<n-1 && s[b+1]>=floor)++b;
    double mid=base+(r+.5)*row;
    double* dst=out+6*count++;
    dst[0]=std::max(base+a*row,mid-width/2);dst[1]=std::min(base+(b+1)*row,mid+width/2);
    dst[2]=mid;dst[3]=value;dst[4]=r;dst[5]=prominence;
  }
  meta[0]=n;meta[1]=row;meta[2]=total;meta[3]=input;meta[4]=base;
  return count;
}
}
