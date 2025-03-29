document.addEventListener('scroll', ()=>{
    const header = document.querySelector('.navbar');
    
    if(window.scrollY > 900){
        header.classList.add('scrolled');
    } else{
        header.classList.remove('scrolled');
    }
});   